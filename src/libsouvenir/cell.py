import asyncio
from gettext import gettext as _, ngettext as _n
from gi.repository import Adw, Gdk, Gio, Gtk
from .model import PhotoItem, PhotoItemState

cells_made = 0

@Gtk.Template(resource_path='/dev/anli/linux/souvenir/ui/cell.ui')
class PhotoCell(Gtk.Widget):
    __gtype_name__ = 'PhotoCell'

    _item: PhotoItem | None = None
    tasks: set
    texture: Gdk.Texture | None = None
    image: Gtk.Picture = Gtk.Template.Child()

    @property
    def item(self) -> PhotoItem | None:
        return self._item

    @item.setter
    def item(self, value: PhotoItem | None):
        if self._item is value:
            return

        for task in self.tasks:
            task.cancel()
        self.tasks.clear()

        if self._item is not None:
            self._item.disconnect_by_func(self.on_item_state_changed)

        self._item = value
        self.texture = None
        self.update_ui()

        if value is None:
            return

        value.connect("state-changed", self.on_item_state_changed)

        app = Gio.Application.get_default()
        assert app is not None
        self.tasks.add(app.create_asyncio_task(self.update_item()))

    serial_number: int

    def __init__(self):
        global cells_made
        self.serial_number = cells_made
        self.tasks = set()
        cells_made += 1
        super().__init__()
        self.update_ui()

    def on_item_state_changed(self, item: PhotoItem):
        self.update_ui()

    def update_ui(self):
        if self.texture is None:
            self.image.set_visible(False)
        else:
            self.image.set_paintable(self.texture)
            self.image.set_visible(True)

    async def update_item(self):
        item = self.item
        if item is None:
            return

        current_task = asyncio.current_task()
        assert current_task is not None

        await asyncio.sleep(0.5)
        if current_task.cancelling():
            return

        await item.load_metadata_if_needed()
        if current_task.cancelling():
            return
        
        texture = await asyncio.shield(item.load_thumbnail_if_needed())
        if current_task.cancelling():
            return

        self.texture = texture
        self.update_ui()

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def do_measure(self, orientation: Gtk.Orientation, for_size: int):
        return (for_size, for_size, -1, -1)

    def do_size_allocate(self, width: int, height: int, baseline: int):
        self.image.allocate(width, height, baseline, None)