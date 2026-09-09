import asyncio
import sys
import gi
import os
from pathlib import Path

from gettext import gettext as _

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.events import GLibEventLoopPolicy
from gi.repository import Gtk, Gdk, Gio, Adw
from .model import PhotoModel
from .window import SouvenirWindow


class SouvenirApplication(Adw.Application):
    """The main application singleton class."""

    model: PhotoModel
    connect_task: asyncio.Task | None

    def __init__(self):
        super().__init__(application_id='dev.anli.linux.souvenir',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/dev/anli/linux/souvenir')
        self.create_action('quit', lambda *_: self.quit(), ['<control>q'])
        self.create_action('about', self.on_about_action)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource('/dev/anli/linux/souvenir/css/style.css')

        display = Gdk.Display.get_default()
        assert display is not None
        Gtk.StyleContext.add_provider_for_display(display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.model = PhotoModel(Path(os.environ["PHOTOS_LIBRARY_PATH"]))

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = SouvenirWindow(self.model, application=self)
        # win.connect("close-request", self.on_close_request)
        win.present()
        self.connect_task = self.create_asyncio_task(self.model.connect_to_db())

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(application_name='Souvenir',
                                application_icon='dev.anli.linux.souvenir',
                                developer_name='Anthony Li',
                                version='0.1.0',
                                # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
                                translator_credits = _('translator-credits'),
                                developers=['Anthony Li'],
                                copyright='© 2026 Anthony Li')
        about.present(self.props.active_window)

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def do_shutdown(self):
        for task in asyncio.all_tasks():
            task.cancel()

        if self.model.db is not None:
            self.model.db.stop()
        Gio.Application.do_shutdown(self)


def main(version):
    """The application's entry point."""
    asyncio.set_event_loop_policy(GLibEventLoopPolicy()) # type: ignore

    app = SouvenirApplication()
    return app.run(sys.argv)