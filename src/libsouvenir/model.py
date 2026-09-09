import aiosqlite
import asyncio
from datetime import datetime
from enum import IntEnum
from gi.repository import Gdk, Gio, Gly, GlyGtk4, GObject
from pathlib import Path

class PhotoItemState(IntEnum):
    PENDING = 0
    LOADING_METADATA = 1
    METADATA = 2

class PhotoItem(GObject.Object):
    __gsignals__ = {
        "state-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    __gtype_name__ = 'PhotoItem'

    index: int
    model: PhotoModel
    _state = PhotoItemState.PENDING
    metadata_event: asyncio.Event
    thumbnail_future: asyncio.Future[Gdk.Texture | None] | None = None

    uuid: str | None = None
    kind: int | None = None
    date_taken: datetime | None = None
    directory: str | None = None
    filename: str | None = None

    @property
    def state(self) -> PhotoItemState:
        return self._state

    @state.setter
    def state(self, value: PhotoItemState):
        if self._state != value:
            self._state = value
            if value == PhotoItemState.METADATA:
                self.metadata_event.set()
            self.emit("state-changed")

    def __init__(self, index: int, model: PhotoModel):
        self.index = index
        self.model = model
        self.metadata_event = asyncio.Event()
        super().__init__()

    async def load_metadata_if_needed(self):
        if self.state == PhotoItemState.PENDING:
            self.state = PhotoItemState.LOADING_METADATA
            await self.model.load_metadata(self.index)
        if self.state < PhotoItemState.METADATA:
            await self.metadata_event.wait()

    async def load_thumbnail_if_needed(self) -> Gdk.Texture | None:
        if not self.uuid:
            return None

        if self.thumbnail_future is not None:
            return await self.thumbnail_future

        self.thumbnail_future = asyncio.Future()
        result = None
        try:
            dir = self.model.path / "resources" / "derivatives" / self.uuid[0]
            files = await asyncio.to_thread(lambda: list(dir.glob(f"{self.uuid}*.jpeg")))
            for file in files:
                file = Gio.File.new_for_path(file.as_posix())
                loader = Gly.Loader.new(file)
                image: Gly.Image = await loader.load_async() # type: ignore
                frame: Gly.Frame | None = await image.next_frame_async() # type: ignore
                if frame:
                    result = GlyGtk4.frame_get_texture(frame)
                    break
        except BaseException as e:
            print(f"Error loading thumbnail for {self.uuid}: {e.with_traceback(e.__traceback__)}")
            result = None

        self.thumbnail_future.set_result(result)
        return result



class PhotoModel(GObject.Object, Gio.ListModel):
    __gsignals__ = {
        "count-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    __gtype_name__ = 'PhotoModel'

    path: Path
    db: aiosqlite.Connection | None = None
    n_items: int | None = None
    cache: dict[int, PhotoItem] = {}
    metadata_batch_size = 256
    metadata_batches_loading = set()


    def __init__(self, path: Path):
        super().__init__()
        self.path = path

    async def connect_to_db(self):
        db_path = self.path / "database" / "Photos.sqlite"

        assert self.db is None
        self.db = await aiosqlite.connect(db_path.as_uri() + "?mode=ro", uri=True)
        print(f"Connected to database at {db_path}")

        cursor = await self.db.execute("SELECT COUNT(*) FROM ZASSET WHERE ZISDETECTEDSCREENSHOT = 0 AND ZHIDDEN = 0 AND ZTRASHEDSTATE = 0")
        row = await cursor.fetchone()
        await cursor.close()

        if row is not None:
            n_items = row[0]
            self.n_items = n_items
            self.items_changed(0, 0, n_items)
            self.emit("count-changed")
            print(f"Found {n_items} items.")

    def do_get_n_items(self):
        return self.n_items if self.n_items is not None else 0

    def do_get_item_type(self):
        return PhotoItem

    def do_get_item(self, position):
        if self.n_items is None or position < 0 or position >= self.n_items:
            return None
        if position not in self.cache:
            self.cache[position] = PhotoItem(position, self)
        return self.cache[position]

    async def load_metadata(self, index: int):
        if self.db is None:
            return

        batch_start = (index // self.metadata_batch_size) * self.metadata_batch_size
        if batch_start in self.metadata_batches_loading:
            return

        self.metadata_batches_loading.add(batch_start)
        cursor = await self.db.execute(
            """
            SELECT
                ZUUID as uuid,

                ZKIND as kind,

                datetime(ZDATECREATED + 978307200, 'unixepoch', 'localtime') AS date_taken,

                ZDIRECTORY as directory,

                ZFILENAME as filename

            FROM ZASSET

            WHERE COALESCE(ZISDETECTEDSCREENSHOT, 0) = 0
            AND COALESCE(ZHIDDEN, 0) = 0
            AND COALESCE(ZTRASHEDSTATE, 0) = 0

            ORDER BY ZDATECREATED DESC

            LIMIT ? OFFSET ?
            """,
            (self.metadata_batch_size, batch_start)
        )

        i = batch_start
        async for row in cursor:
            item = self.cache.get(i)
            if item is None:
                item = PhotoItem(i, self)
                item.state = PhotoItemState.LOADING_METADATA
                self.cache[i] = item
            uuid, kind, date_taken, directory, filename = row
            item.uuid = uuid
            item.kind = kind
            item.date_taken = datetime.strptime(date_taken, "%Y-%m-%d %H:%M:%S") if date_taken is not None else None
            item.directory = directory
            item.filename = filename
            if item.state < PhotoItemState.METADATA:
                item.state = PhotoItemState.METADATA
            i += 1
        
        await cursor.close()
        self.metadata_batches_loading.remove(batch_start)

        