from gettext import gettext as _, ngettext as _n
from gi.repository import Adw, Gtk
from .cell import PhotoCell
from .model import PhotoItem, PhotoModel

@Gtk.Template(resource_path='/dev/anli/linux/souvenir/ui/window.ui')
class SouvenirWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'SouvenirWindow'

    grid: Gtk.GridView = Gtk.Template.Child()
    header_bar: Adw.HeaderBar = Gtk.Template.Child()
    model: PhotoModel

    def __init__(self, model: PhotoModel, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.header_bar.set_title_widget(Adw.WindowTitle.new(_("Souvenir"), ""))
        self.update_subtitle()
        self.model.connect("count-changed", self.on_model_count_changed)

        self.grid.set_model(Gtk.SingleSelection(model=model))

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.on_factory_setup)
        factory.connect("bind", self.on_factory_bind)
        self.grid.set_factory(factory)

    def update_subtitle(self):
        title_widget = self.header_bar.get_title_widget()
        if not isinstance(title_widget, Adw.WindowTitle):
            return

        if self.model.n_items is not None:
            title_widget.set_subtitle(_n("{n} item", "{n} items", self.model.n_items).format(n=self.model.n_items))
        else:
            title_widget.set_subtitle(_("Loading..."))

    def on_model_count_changed(self, model: PhotoModel):
        self.update_subtitle()

    def on_factory_setup(self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem):
        item = list_item.get_item()
        cell = PhotoCell()
        if isinstance(item, PhotoItem):
            cell.item = item
        
        list_item.set_child(cell)

    def on_factory_bind(self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem):
        item = list_item.get_item()
        if not isinstance(item, PhotoItem):
            return

        child = list_item.get_child()
        if not isinstance(child, PhotoCell):
            return

        child.item = item
