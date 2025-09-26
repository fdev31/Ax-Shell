import json
import os
import subprocess
import time

import gi

gi.require_version("Gtk", "3.0")
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.image import Image as FabricImage
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.stack import Stack
from fabric.widgets.window import Window
from gi.repository import GdkPixbuf, GLib, Gtk, Gdk
from PIL import Image

from .data import (
    APP_NAME,
    APP_NAME_CAP,
    NOTIF_POS_DEFAULT,
    NOTIF_POS_KEY,
    PANEL_POSITION_DEFAULT,
    PANEL_POSITION_KEY,
)
from .settings_utils import backup_and_replace, bind_vars, start_config
from .fabric_declarative import FabricUIBuilder


class HyprConfGUI(Window):
    def __init__(self, show_lock_checkbox: bool, show_idle_checkbox: bool, **kwargs):
        super().__init__(
            title="Ax-Shell Settings",
            name="axshell-settings-window",
            size=(640, 640),
            **kwargs,
        )

        self.set_resizable(False)

        self.selected_face_icon = None
        self.show_lock_checkbox = show_lock_checkbox
        self.show_idle_checkbox = show_idle_checkbox

        # Initialize UI builder
        self.builder = FabricUIBuilder(self)

        # Load base UI structure from YAML
        yaml_path = os.path.join(os.path.dirname(__file__), "settings_gui.yaml")
        self.root_box = self.builder.load_from_yaml(yaml_path)
        self.add(self.root_box)

        # Create tab contents
        self.key_bindings_tab_content = self.create_key_bindings_tab()
        self.appearance_tab_content = self.create_appearance_tab()
        self.system_tab_content = self.create_system_tab()
        self.about_tab_content = self.create_about_tab()

        # Add tabs to stack
        self.tab_stack = self.builder.get_widget("tab_stack")
        self.tab_stack.add_titled(
            self.key_bindings_tab_content, "key_bindings", "Key Bindings"
        )
        self.tab_stack.add_titled(
            self.appearance_tab_content, "appearance", "Appearance"
        )
        self.tab_stack.add_titled(self.system_tab_content, "system", "System")
        self.tab_stack.add_titled(self.about_tab_content, "about", "About")

    def create_key_bindings_tab(self):
        keybind_grid = self.builder.get_widget("keybind_grid")

        self.entries = []
        bindings = [
            (f"Reload {APP_NAME_CAP}", "prefix_restart", "suffix_restart"),
            ("Message", "prefix_axmsg", "suffix_axmsg"),
            ("Dashboard", "prefix_dash", "suffix_dash"),
            ("Bluetooth", "prefix_bluetooth", "suffix_bluetooth"),
            ("Pins", "prefix_pins", "suffix_pins"),
            ("Kanban", "prefix_kanban", "suffix_kanban"),
            ("App Launcher", "prefix_launcher", "suffix_launcher"),
            ("Tmux", "prefix_tmux", "suffix_tmux"),
            ("Clipboard History", "prefix_cliphist", "suffix_cliphist"),
            ("Toolbox", "prefix_toolbox", "suffix_toolbox"),
            ("Overview", "prefix_overview", "suffix_overview"),
            ("Wallpapers", "prefix_wallpapers", "suffix_wallpapers"),
            ("Random Wallpaper", "prefix_randwall", "suffix_randwall"),
            ("Audio Mixer", "prefix_mixer", "suffix_mixer"),
            ("Emoji Picker", "prefix_emoji", "suffix_emoji"),
            ("Power Menu", "prefix_power", "suffix_power"),
            ("Toggle Caffeine", "prefix_caffeine", "suffix_caffeine"),
            ("Toggle Bar", "prefix_toggle", "suffix_toggle"),
            ("Reload CSS", "prefix_css", "suffix_css"),
            (
                "Restart with inspector",
                "prefix_restart_inspector",
                "suffix_restart_inspector",
            ),
        ]

        for i, (label_text, prefix_key, suffix_key) in enumerate(bindings):
            row = i + 1
            binding_label = Label(label=label_text, h_align="start")
            keybind_grid.attach(binding_label, 0, row, 1, 1)
            prefix_entry = Entry(text=bind_vars.get(prefix_key, ""))
            keybind_grid.attach(prefix_entry, 1, row, 1, 1)
            plus_label = Label(label="+", h_align="center")
            keybind_grid.attach(plus_label, 2, row, 1, 1)
            suffix_entry = Entry(text=bind_vars.get(suffix_key, ""))
            keybind_grid.attach(suffix_entry, 3, row, 1, 1)
            self.entries.append((prefix_key, suffix_key, prefix_entry, suffix_entry))

        return self.builder.get_widget("key_bindings_tab_content")

    def create_appearance_tab(self):
        # Get widget references from the builder
        self.wall_dir_chooser = self.builder.get_widget("wall_dir_chooser")
        self.face_image = self.builder.get_widget("face_image")
        self.face_status_label = self.builder.get_widget("face_status_label")
        self.datetime_12h_switch = self.builder.get_widget("datetime_12h_switch")
        self.position_combo = self.builder.get_widget("position_combo")
        self.centered_switch = self.builder.get_widget("centered_switch")
        self.dock_switch = self.builder.get_widget("dock_switch")
        self.dock_hover_switch = self.builder.get_widget("dock_hover_switch")
        self.dock_size_scale = self.builder.get_widget("dock_size_scale")
        self.ws_num_switch = self.builder.get_widget("ws_num_switch")
        self.ws_chinese_switch = self.builder.get_widget("ws_chinese_switch")
        self.special_ws_switch = self.builder.get_widget("special_ws_switch")
        self.bar_theme_combo = self.builder.get_widget("bar_theme_combo")
        self.dock_theme_combo = self.builder.get_widget("dock_theme_combo")
        self.panel_theme_combo = self.builder.get_widget("panel_theme_combo")
        self.panel_position_combo = self.builder.get_widget("panel_position_combo")
        self.notification_pos_combo = self.builder.get_widget("notification_pos_combo")
        components_grid = self.builder.get_widget("components_grid")

        # Populate widgets with data from bind_vars
        self.wall_dir_chooser.set_filename(bind_vars.get("wallpapers_dir", ""))

        current_face = os.path.expanduser("~/.face.icon")
        try:
            if os.path.exists(current_face):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(current_face, 64, 64)
                self.face_image.set_from_pixbuf(pixbuf)
            else:
                self.face_image.set_from_icon_name("user-info", Gtk.IconSize.DIALOG)
        except Exception as e:
            print(f"Error loading face icon: {e}")
            self.face_image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)

        self.datetime_12h_switch.set_active(bind_vars.get("datetime_12h_format", False))

        positions = ["Top", "Bottom", "Left", "Right"]
        current_position = bind_vars.get("bar_position", "Top")
        try:
            self.position_combo.set_active(positions.index(current_position))
        except ValueError:
            self.position_combo.set_active(0)

        self.centered_switch.set_active(bind_vars.get("centered_bar", False))
        self.centered_switch.set_sensitive(current_position in ["Left", "Right"])

        self.dock_switch.set_active(bind_vars.get("dock_enabled", True))
        self.dock_hover_switch.set_active(bind_vars.get("dock_always_show", False))
        self.dock_hover_switch.set_sensitive(self.dock_switch.get_active())

        self.dock_size_scale.set_value(bind_vars.get("dock_icon_size", 28))

        self.ws_num_switch.set_active(bind_vars.get("bar_workspace_show_number", False))
        self.ws_chinese_switch.set_active(bind_vars.get("bar_workspace_use_chinese_numerals", False))
        self.ws_chinese_switch.set_sensitive(self.ws_num_switch.get_active())

        self.special_ws_switch.set_active(bind_vars.get("bar_hide_special_workspace", True))

        themes = ["Pills", "Dense", "Edge"]
        current_theme = bind_vars.get("bar_theme", "Pills")
        try:
            self.bar_theme_combo.set_active(themes.index(current_theme))
        except ValueError:
            self.bar_theme_combo.set_active(0)

        current_dock_theme = bind_vars.get("dock_theme", "Pills")
        try:
            self.dock_theme_combo.set_active(themes.index(current_dock_theme))
        except ValueError:
            self.dock_theme_combo.set_active(0)

        panel_themes = ["Notch", "Panel"]
        current_panel_theme = bind_vars.get("panel_theme", "Notch")
        try:
            self.panel_theme_combo.set_active(panel_themes.index(current_panel_theme))
        except ValueError:
            self.panel_theme_combo.set_active(0)

        self.panel_position_options = ["Start", "Center", "End"]
        current_panel_position = bind_vars.get(PANEL_POSITION_KEY, PANEL_POSITION_DEFAULT)
        try:
            self.panel_position_combo.set_active(self.panel_position_options.index(current_panel_position))
        except ValueError:
            self.panel_position_combo.set_active(0)

        notification_positions_list = ["Top", "Bottom"]
        current_notif_pos = bind_vars.get(NOTIF_POS_KEY, NOTIF_POS_DEFAULT)
        try:
            self.notification_pos_combo.set_active(notification_positions_list.index(current_notif_pos))
        except ValueError:
            self.notification_pos_combo.set_active(0)

        self.component_switches = {}
        component_display_names = {
            "button_apps": "App Launcher Button",
            "systray": "System Tray",
            "control": "Control Panel",
            "network": "Network Applet",
            "button_tools": "Toolbox Button",
            "sysprofiles": "Powerprofiles Switcher",
            "button_overview": "Overview Button",
            "ws_container": "Workspaces",
            "weather": "Weather Widget",
            "battery": "Battery Indicator",
            "metrics": "System Metrics",
            "language": "Language Indicator",
            "date_time": "Date & Time",
            "button_power": "Power Button",
        }

        self.corners_switch = self.builder.get_widget("corners_switch")
        self.corners_switch.set_active(bind_vars.get("corners_visible", True))

        self.component_switches = {}
        component_display_names = {
            "button_apps": "App Launcher Button",
            "systray": "System Tray",
            "control": "Control Panel",
            "network": "Network Applet",
            "button_tools": "Toolbox Button",
            "sysprofiles": "Powerprofiles Switcher",
            "button_overview": "Overview Button",
            "ws_container": "Workspaces",
            "weather": "Weather Widget",
            "battery": "Battery Indicator",
            "metrics": "System Metrics",
            "language": "Language Indicator",
            "date_time": "Date & Time",
            "button_power": "Power Button",
        }

        num_components = len(component_display_names)
        rows_per_column = (num_components + 2) // 2

        item_idx = 0
        for name, display in component_display_names.items():
            row = item_idx % rows_per_column + 1
            col = (item_idx // rows_per_column) * 2

            component_label = Label(label=display, h_align="start", v_align="center")
            components_grid.attach(component_label, col, row, 1, 1)

            switch_container = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                halign=Gtk.Align.START,
                valign=Gtk.Align.CENTER,
            )
            component_switch = Gtk.Switch(active=bind_vars.get(f"bar_{name}_visible", True))
            switch_container.add(component_switch)
            components_grid.attach(switch_container, col + 1, row, 1, 1)
            self.component_switches[name] = component_switch
            item_idx += 1

        self._update_panel_position_sensitivity()
        return self.builder.get_widget("appearance_tab_content")

    def create_system_tab(self):
        # Get widget references from the builder
        system_grid = self.builder.get_widget("system_grid")
        self.auto_append_switch = self.builder.get_widget("auto_append_switch")
        self.monitor_selection_container = self.builder.get_widget("monitor_selection_container")
        self.terminal_entry = self.builder.get_widget("terminal_entry")
        notif_grid = self.builder.get_widget("notif_grid")
        self.limited_apps_entry = self.builder.get_widget("limited_apps_entry")
        self.ignored_apps_entry = self.builder.get_widget("ignored_apps_entry")
        metrics_grid = self.builder.get_widget("metrics_grid")
        self.disk_entries = self.builder.get_widget("disk_entries")

        # Populate widgets with data from bind_vars
        self.auto_append_switch.set_active(bind_vars.get("auto_append_hyprland", True))

        self.monitor_checkboxes = {}
        try:
            from utils.monitor_manager import get_monitor_manager
            monitor_manager = get_monitor_manager()
            available_monitors = monitor_manager.get_monitors()
        except (ImportError, Exception) as e:
            print(f"Could not get monitor info for settings: {e}")
            available_monitors = [{'id': 0, 'name': 'default'}]

        current_selection = bind_vars.get("selected_monitors", [])
        for monitor in available_monitors:
            monitor_name = monitor.get('name', f'monitor-{monitor.get("id", 0)}')
            checkbox_container = Box(orientation="h", spacing=5, h_align="start")
            checkbox = Gtk.CheckButton(label=monitor_name)
            is_selected = len(current_selection) == 0 or monitor_name in current_selection
            checkbox.set_active(is_selected)
            checkbox_container.add(checkbox)
            self.monitor_selection_container.add(checkbox_container)
            self.monitor_checkboxes[monitor_name] = checkbox

        hint_label = Label(markup="<small>Leave all unchecked to show on all monitors</small>", h_align="start")
        self.monitor_selection_container.add(hint_label)

        self.terminal_entry.set_text(bind_vars.get("terminal_command", "kitty -e"))

        row = 4
        self.lock_switch = None
        if self.show_lock_checkbox:
            lock_label = Label(label="Replace Hyprlock config", h_align="start", v_align="center")
            system_grid.attach(lock_label, 2, row, 1, 1)
            lock_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
            self.lock_switch = Gtk.Switch(tooltip_text="Replace Hyprlock configuration with Ax-Shell's custom config")
            lock_switch_container.add(self.lock_switch)
            system_grid.attach(lock_switch_container, 3, row, 1, 1)
            row += 1
        self.idle_switch = None
        if self.show_idle_checkbox:
            idle_label = Label(label="Replace Hypridle config", h_align="start", v_align="center")
            system_grid.attach(idle_label, 2, row, 1, 1)
            idle_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
            self.idle_switch = Gtk.Switch(tooltip_text="Replace Hypridle configuration with Ax-Shell's custom config")
            idle_switch_container.add(self.idle_switch)
            system_grid.attach(idle_switch_container, 3, row, 1, 1)
            row += 1
        if self.show_lock_checkbox or self.show_idle_checkbox:
            note_label = Label(markup="<small>Existing configs will be backed up</small>", h_align="start")
            system_grid.attach(note_label, 2, row, 2, 1)

        limited_apps_list = bind_vars.get("limited_apps_history", ["Spotify"])
        limited_apps_text = ", ".join(f'"{app}"' for app in limited_apps_list)
        self.limited_apps_entry.set_text(limited_apps_text)

        ignored_apps_list = bind_vars.get("history_ignored_apps", ["Hyprshot"])
        ignored_apps_text = ", ".join(f'"{app}"' for app in ignored_apps_list)
        self.ignored_apps_entry.set_text(ignored_apps_text)

        self.metrics_switches = {}
        self.metrics_small_switches = {}
        metric_names = {"cpu": "CPU", "ram": "RAM", "disk": "Disk", "gpu": "GPU"}

        metrics_grid.attach(Label(label="Show in Metrics", h_align="start"), 0, 0, 1, 1)
        for i, (key, label_text) in enumerate(metric_names.items()):
            switch = Gtk.Switch(active=bind_vars.get("metrics_visible", {}).get(key, True))
            self.metrics_switches[key] = switch
            metrics_grid.attach(Label(label=label_text, h_align="start"), 0, i + 1, 1, 1)
            metrics_grid.attach(switch, 1, i + 1, 1, 1)

        metrics_grid.attach(Label(label="Show in Small Metrics", h_align="start"), 2, 0, 1, 1)
        for i, (key, label_text) in enumerate(metric_names.items()):
            switch = Gtk.Switch(active=bind_vars.get("metrics_small_visible", {}).get(key, True))
            self.metrics_small_switches[key] = switch
            metrics_grid.attach(Label(label=label_text, h_align="start"), 2, i + 1, 1, 1)
            metrics_grid.attach(switch, 3, i + 1, 1, 1)

        def enforce_minimum_metrics(switch_dict):
            enabled_switches = [s for s in switch_dict.values() if s.get_active()]
            can_disable = len(enabled_switches) > 3
            for s in switch_dict.values():
                s.set_sensitive(True if can_disable or not s.get_active() else False)

        def on_metric_toggle(switch, gparam, switch_dict):
            enforce_minimum_metrics(switch_dict)

        for k_s, s_s in self.metrics_switches.items():
            s_s.connect("notify::active", on_metric_toggle, self.metrics_switches)
        for k_s, s_s in self.metrics_small_switches.items():
            s_s.connect("notify::active", on_metric_toggle, self.metrics_small_switches)
        enforce_minimum_metrics(self.metrics_switches)
        enforce_minimum_metrics(self.metrics_small_switches)

        for p in bind_vars.get("bar_metrics_disks", ["/"]):
            self._add_disk_entry_widget(p)

        return self.builder.get_widget("system_tab_content")

    def on_add_disk_entry(self, _):
        self._add_disk_entry_widget("/")

    def _add_disk_entry_widget(self, path):
        """Helper para añadir una fila de entrada de disco al Box disk_entries."""
        bar = Box(orientation="h", spacing=10, h_align="start")
        entry = Entry(text=path, h_expand=True)
        bar.add(entry)
        x_btn = Button(label="X")
        x_btn.connect(
            "clicked",
            lambda _, current_bar_to_remove=bar: self.disk_entries.remove(
                current_bar_to_remove
            ),
        )
        bar.add(x_btn)
        self.disk_entries.add(bar)
        self.disk_entries.show_all()

    def create_about_tab(self):
        return self.builder.get_widget("about_tab_content")

    def on_kofi_clicked(self, _):
        import webbrowser
        webbrowser.open("https://ko-fi.com/Axenide")

    # Include all the handler methods from the original class
    def on_ws_num_changed(self, switch, gparam):
        is_active = switch.get_active()
        self.ws_chinese_switch.set_sensitive(is_active)
        if not is_active:
            self.ws_chinese_switch.set_active(False)

    def on_position_changed(self, combo):
        position = combo.get_active_text()
        is_vertical = position in ["Left", "Right"]
        self.centered_switch.set_sensitive(is_vertical)
        if not is_vertical:
            self.centered_switch.set_active(False)

    def on_dock_enabled_changed(self, switch, gparam):
        is_active = switch.get_active()
        self.dock_hover_switch.set_sensitive(is_active)
        if not is_active:
            self.dock_hover_switch.set_active(False)

    def _on_panel_theme_changed_for_position_sensitivity(self, combo):
        self._update_panel_position_sensitivity()

    def _update_panel_position_sensitivity(self):
        if hasattr(self, "panel_theme_combo") and hasattr(self, "panel_position_combo"):
            selected_theme = self.panel_theme_combo.get_active_text()
            is_panel_theme_selected = selected_theme == "Panel"
            self.panel_position_combo.set_sensitive(is_panel_theme_selected)

    def on_notification_position_changed(self, combo: Gtk.ComboBoxText):
        selected_text = combo.get_active_text()
        if selected_text:
            bind_vars[NOTIF_POS_KEY] = selected_text
            print(
                f"Notification position updated in bind_vars: {bind_vars[NOTIF_POS_KEY]}"
            )

    def on_notification_position_changed(self, combo: Gtk.ComboBoxText):
        selected_text = combo.get_active_text()
        if selected_text:
            bind_vars[NOTIF_POS_KEY] = selected_text
            print(
                f"Notification position updated in bind_vars: {bind_vars[NOTIF_POS_KEY]}"
            )

    def on_ws_num_changed(self, switch, gparam):
        is_active = switch.get_active()
        self.ws_chinese_switch.set_sensitive(is_active)
        if not is_active:
            self.ws_chinese_switch.set_active(False)

    def on_position_changed(self, combo):
        position = combo.get_active_text()
        is_vertical = position in ["Left", "Right"]
        self.centered_switch.set_sensitive(is_vertical)
        if not is_vertical:
            self.centered_switch.set_active(False)

    def on_dock_enabled_changed(self, switch, gparam):
        is_active = switch.get_active()
        self.dock_hover_switch.set_sensitive(is_active)
        if not is_active:
            self.dock_hover_switch.set_active(False)

    def on_select_face_icon(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Select Face Icon",
            transient_for=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )
        image_filter = Gtk.FileFilter()
        image_filter.set_name("Image files")
        for mime in ["image/png", "image/jpeg"]:
            image_filter.add_mime_type(mime)
        for pattern in ["*.png", "*.jpg", "*.jpeg"]:
            image_filter.add_pattern(pattern)
        dialog.add_filter(image_filter)
        if dialog.run() == Gtk.ResponseType.OK:
            self.selected_face_icon = dialog.get_filename()
            self.face_status_label.label = (
                f"Selected: {os.path.basename(self.selected_face_icon)}"
            )
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    self.selected_face_icon, 64, 64
                )
                self.face_image.set_from_pixbuf(pixbuf)
            except Exception as e:
                print(f"Error loading selected face icon preview: {e}")
                self.face_image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        dialog.destroy()

    def on_accept(self, widget):
        current_bind_vars_snapshot = {}
        for prefix_key, suffix_key, prefix_entry, suffix_entry in self.entries:
            current_bind_vars_snapshot[prefix_key] = prefix_entry.get_text()
            current_bind_vars_snapshot[suffix_key] = suffix_entry.get_text()

        current_bind_vars_snapshot["wallpapers_dir"] = (
            self.wall_dir_chooser.get_filename()
        )

        current_bind_vars_snapshot["bar_position"] = (
            self.position_combo.get_active_text()
        )
        current_bind_vars_snapshot["vertical"] = current_bind_vars_snapshot[
            "bar_position"
        ] in ["Left", "Right"]

        current_bind_vars_snapshot["centered_bar"] = self.centered_switch.get_active()
        current_bind_vars_snapshot["datetime_12h_format"] = (
            self.datetime_12h_switch.get_active()
        )
        current_bind_vars_snapshot["dock_enabled"] = self.dock_switch.get_active()
        current_bind_vars_snapshot["dock_always_show"] = (
            self.dock_hover_switch.get_active()
        )
        current_bind_vars_snapshot["dock_icon_size"] = int(self.dock_size_scale.value)
        current_bind_vars_snapshot["terminal_command"] = self.terminal_entry.get_text()
        current_bind_vars_snapshot["auto_append_hyprland"] = (
            self.auto_append_switch.get_active()
        )
        current_bind_vars_snapshot["corners_visible"] = self.corners_switch.get_active()
        current_bind_vars_snapshot["bar_workspace_show_number"] = (
            self.ws_num_switch.get_active()
        )
        current_bind_vars_snapshot["bar_workspace_use_chinese_numerals"] = (
            self.ws_chinese_switch.get_active()
        )
        current_bind_vars_snapshot["bar_hide_special_workspace"] = (
            self.special_ws_switch.get_active()
        )
        current_bind_vars_snapshot["bar_theme"] = self.bar_theme_combo.get_active_text()
        current_bind_vars_snapshot["dock_theme"] = (
            self.dock_theme_combo.get_active_text()
        )
        current_bind_vars_snapshot["panel_theme"] = (
            self.panel_theme_combo.get_active_text()
        )
        current_bind_vars_snapshot[PANEL_POSITION_KEY] = (
            self.panel_position_combo.get_active_text()
        )
        selected_notif_pos_text = self.notification_pos_combo.get_active_text()
        if selected_notif_pos_text:
            current_bind_vars_snapshot[NOTIF_POS_KEY] = selected_notif_pos_text
        else:
            current_bind_vars_snapshot[NOTIF_POS_KEY] = NOTIF_POS_DEFAULT

        for component_name, switch in self.component_switches.items():
            current_bind_vars_snapshot[f"bar_{component_name}_visible"] = (
                switch.get_active()
            )

        current_bind_vars_snapshot["metrics_visible"] = {
            k: s.get_active() for k, s in self.metrics_switches.items()
        }
        current_bind_vars_snapshot["metrics_small_visible"] = {
            k: s.get_active() for k, s in self.metrics_small_switches.items()
        }
        current_bind_vars_snapshot["bar_metrics_disks"] = [
            child.get_children()[0].get_text()
            for child in self.disk_entries.get_children()
            if isinstance(child, Gtk.Box)
            and child.get_children()
            and isinstance(child.get_children()[0], Entry)
        ]

        # Parse notification app lists
        def parse_app_list(text):
            """Parse comma-separated app names with quotes"""
            if not text.strip():
                return []
            apps = []
            for app in text.split(","):
                app = app.strip()
                if app.startswith('"') and app.endswith('"'):
                    app = app[1:-1]
                elif app.startswith("'") and app.endswith("'"):
                    app = app[1:-1]
                if app:
                    apps.append(app)
            return apps

        current_bind_vars_snapshot["limited_apps_history"] = parse_app_list(
            self.limited_apps_entry.get_text()
        )
        current_bind_vars_snapshot["history_ignored_apps"] = parse_app_list(
            self.ignored_apps_entry.get_text()
        )

        # Save monitor selection
        selected_monitors = []
        any_checked = False
        for monitor_name, checkbox in self.monitor_checkboxes.items():
            if checkbox.get_active():
                selected_monitors.append(monitor_name)
                any_checked = True

        # If no monitors are checked, use empty array (means show on all monitors)
        current_bind_vars_snapshot["selected_monitors"] = (
            selected_monitors if any_checked else []
        )

        selected_icon_path = self.selected_face_icon
        replace_lock = self.lock_switch and self.lock_switch.get_active()
        replace_idle = self.idle_switch and self.idle_switch.get_active()

        if self.selected_face_icon:
            self.selected_face_icon = None
            self.face_status_label.label = ""

        def _apply_and_reload_task_thread(user_data):
            nonlocal current_bind_vars_snapshot

            from . import settings_utils

            settings_utils.bind_vars.clear()
            settings_utils.bind_vars.update(current_bind_vars_snapshot)

            start_time = time.time()
            print(f"{start_time:.4f}: Background task started.")

            config_json = os.path.expanduser(
                f"~/.config/{APP_NAME_CAP}/config/config.json"
            )
            os.makedirs(os.path.dirname(config_json), exist_ok=True)
            try:
                with open(config_json, "w") as f:
                    json.dump(settings_utils.bind_vars, f, indent=4)
                print(f"{time.time():.4f}: Saved config.json.")
            except Exception as e:
                print(f"Error saving config.json: {e}")

            if selected_icon_path:
                print(f"{time.time():.4f}: Processing face icon...")
                try:
                    img = Image.open(selected_icon_path)
                    side = min(img.size)
                    left = (img.width - side) // 2
                    top = (img.height - side) // 2
                    cropped_img = img.crop((left, top, left + side, top + side))
                    face_icon_dest = os.path.expanduser("~/.face.icon")
                    cropped_img.save(face_icon_dest, format="PNG")
                    print(f"{time.time():.4f}: Face icon saved to {face_icon_dest}")
                    GLib.idle_add(self._update_face_image_widget, face_icon_dest)
                except Exception as e:
                    print(f"Error processing face icon: {e}")
                print(f"{time.time():.4f}: Finished processing face icon.")

            if replace_lock:
                print(f"{time.time():.4f}: Replacing hyprlock config...")
                src = os.path.expanduser(
                    f"~/.config/{APP_NAME_CAP}/config/hypr/hyprlock.conf"
                )
                dest = os.path.expanduser("~/.config/hypr/hyprlock.conf")
                if os.path.exists(src):
                    backup_and_replace(src, dest, "Hyprlock")
                else:
                    print(f"Warning: Source hyprlock config not found at {src}")
                print(f"{time.time():.4f}: Finished replacing hyprlock config.")

            if replace_idle:
                print(f"{time.time():.4f}: Replacing hypridle config...")
                src = os.path.expanduser(
                    f"~/.config/{APP_NAME_CAP}/config/hypr/hypridle.conf"
                )
                dest = os.path.expanduser("~/.config/hypr/hypridle.conf")
                if os.path.exists(src):
                    backup_and_replace(src, dest, "Hypridle")
                else:
                    print(f"Warning: Source hypridle config not found at {src}")
                print(f"{time.time():.4f}: Finished replacing hypridle config.")

            print(
                f"{time.time():.4f}: Checking/Appending hyprland.conf source string..."
            )
            hypr_path = os.path.expanduser("~/.config/hypr/hyprland.conf")
            try:
                from .settings_constants import SOURCE_STRING

                # Check if auto-append is enabled
                auto_append_enabled = current_bind_vars_snapshot.get(
                    "auto_append_hyprland", True
                )
                if auto_append_enabled:
                    needs_append = True
                    if os.path.exists(hypr_path):
                        with open(hypr_path, "r") as f:
                            if SOURCE_STRING.strip() in f.read():
                                needs_append = False
                    else:
                        os.makedirs(os.path.dirname(hypr_path), exist_ok=True)

                    if needs_append:
                        with open(hypr_path, "a") as f:
                            f.write("\n" + SOURCE_STRING)
                        print(f"Appended source string to {hypr_path}")
                    else:
                        print("Source string already present in hyprland.conf")
                else:
                    print("Auto-append to hyprland.conf is disabled")
            except Exception as e:
                print(f"Error updating {hypr_path}: {e}")
            print(
                f"{time.time():.4f}: Finished checking/appending hyprland.conf source string."
            )

            print(f"{time.time():.4f}: Running start_config()...")
            start_config()
            print(f"{time.time():.4f}: Finished start_config().")

            print(f"{time.time():.4f}: Initiating Ax-Shell restart using Popen...")
            main_py = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/main.py")
            kill_cmd = f"killall {APP_NAME}"
            start_cmd = ["uwsm", "app", "--", "python", main_py]
            try:
                kill_proc = subprocess.Popen(
                    kill_cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                kill_proc.wait(timeout=2)
                print(f"{time.time():.4f}: killall process finished (o timed out).")
            except subprocess.TimeoutExpired:
                print("Warning: killall command timed out.")
            except Exception as e:
                print(f"Error running killall: {e}")

            try:
                subprocess.Popen(
                    start_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                print(f"{APP_NAME_CAP} restart initiated via Popen.")
            except FileNotFoundError as e:
                print(f"Error restarting {APP_NAME_CAP}: Command not found ({e})")
            except Exception as e:
                print(f"Error restarting {APP_NAME_CAP} via Popen: {e}")

            print(f"{time.time():.4f}: Ax-Shell restart commands issued via Popen.")
            end_time = time.time()
            print(
                f"{end_time:.4f}: Background task finished (Total: {end_time - start_time:.4f}s)."
            )

        GLib.Thread.new("apply-reload-task", _apply_and_reload_task_thread, None)
        print("Configuration apply/reload task started in background.")

    def _update_face_image_widget(self, icon_path):
        try:
            if self.face_image and self.face_image.get_window():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 64, 64)
                self.face_image.set_from_pixbuf(pixbuf)
        except Exception as e:
            print(f"Error reloading face icon preview: {e}")
            if self.face_image and self.face_image.get_window():
                self.face_image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        return GLib.SOURCE_REMOVE

    def on_reset(self, widget):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Reset all settings to defaults?",
        )
        dialog.format_secondary_text(
            "This will reset all keybindings and appearance settings to their default values."
        )
        if dialog.run() == Gtk.ResponseType.YES:
            from . import settings_utils
            from .settings_constants import DEFAULTS

            settings_utils.bind_vars.clear()
            settings_utils.bind_vars.update(DEFAULTS.copy())

            for prefix_key, suffix_key, prefix_entry, suffix_entry in self.entries:
                prefix_entry.set_text(settings_utils.bind_vars[prefix_key])
                suffix_entry.set_text(settings_utils.bind_vars[suffix_key])

            self.wall_dir_chooser.set_filename(
                settings_utils.bind_vars["wallpapers_dir"]
            )

            positions = ["Top", "Bottom", "Left", "Right"]
            default_position = DEFAULTS.get("bar_position", "Top")
            try:
                self.position_combo.set_active(positions.index(default_position))
            except ValueError:
                self.position_combo.set_active(0)

            self.centered_switch.set_active(
                settings_utils.bind_vars.get("centered_bar", False)
            )
            self.centered_switch.set_sensitive(default_position in ["Left", "Right"])

            self.datetime_12h_switch.set_active(
                settings_utils.bind_vars.get("datetime_12h_format", False)
            )

            self.dock_switch.set_active(
                settings_utils.bind_vars.get("dock_enabled", True)
            )
            self.dock_hover_switch.set_active(
                settings_utils.bind_vars.get("dock_always_show", False)
            )
            self.dock_hover_switch.set_sensitive(self.dock_switch.get_active())
            self.dock_size_scale.set_value(
                settings_utils.bind_vars.get("dock_icon_size", 28)
            )
            self.terminal_entry.set_text(settings_utils.bind_vars["terminal_command"])
            self.auto_append_switch.set_active(
                settings_utils.bind_vars.get("auto_append_hyprland", True)
            )
            self.ws_num_switch.set_active(
                settings_utils.bind_vars.get("bar_workspace_show_number", False)
            )
            self.ws_chinese_switch.set_active(
                settings_utils.bind_vars.get(
                    "bar_workspace_use_chinese_numerals", False
                )
            )
            self.ws_chinese_switch.set_sensitive(self.ws_num_switch.get_active())
            self.special_ws_switch.set_active(
                settings_utils.bind_vars.get("bar_hide_special_workspace", True)
            )

            default_theme_val = DEFAULTS.get("bar_theme", "Pills")
            themes = ["Pills", "Dense", "Edge"]
            try:
                self.bar_theme_combo.set_active(themes.index(default_theme_val))
            except ValueError:
                self.bar_theme_combo.set_active(0)

            default_dock_theme_val = DEFAULTS.get("dock_theme", "Pills")
            try:
                self.dock_theme_combo.set_active(themes.index(default_dock_theme_val))
            except ValueError:
                self.dock_theme_combo.set_active(0)

            default_panel_theme_val = DEFAULTS.get("panel_theme", "Notch")
            panel_themes_options = ["Notch", "Panel"]
            try:
                self.panel_theme_combo.set_active(
                    panel_themes_options.index(default_panel_theme_val)
                )
            except ValueError:
                self.panel_theme_combo.set_active(0)

            default_panel_position_val = DEFAULTS.get(
                PANEL_POSITION_KEY, PANEL_POSITION_DEFAULT
            )
            try:
                self.panel_position_combo.set_active(
                    self.panel_position_options.index(default_panel_position_val)
                )
            except ValueError:
                try:
                    self.panel_position_combo.set_active(
                        self.panel_position_options.index(PANEL_POSITION_DEFAULT)
                    )
                except ValueError:
                    self.panel_position_combo.set_active(0)

            default_notif_pos_val = DEFAULTS.get(NOTIF_POS_KEY, NOTIF_POS_DEFAULT)
            notification_positions_list = ["Top", "Bottom"]
            try:
                self.notification_pos_combo.set_active(
                    notification_positions_list.index(default_notif_pos_val)
                )
            except ValueError:
                self.notification_pos_combo.set_active(0)

            for name, switch in self.component_switches.items():
                switch.set_active(
                    settings_utils.bind_vars.get(f"bar_{name}_visible", True)
                )
            self.corners_switch.set_active(
                settings_utils.bind_vars.get("corners_visible", True)
            )

            metrics_vis_defaults = DEFAULTS.get("metrics_visible", {})
            for k, s_widget in self.metrics_switches.items():
                s_widget.set_active(metrics_vis_defaults.get(k, True))

            metrics_small_vis_defaults = DEFAULTS.get("metrics_small_visible", {})
            for k, s_widget in self.metrics_small_switches.items():
                s_widget.set_active(metrics_small_vis_defaults.get(k, True))

            def enforce_minimum_metrics(switch_dict):
                enabled_switches = [
                    s_widget
                    for s_widget in switch_dict.values()
                    if s_widget.get_active()
                ]
                can_disable = len(enabled_switches) > 3
                for s_widget in switch_dict.values():
                    s_widget.set_sensitive(
                        True if can_disable or not s_widget.get_active() else False
                    )

            enforce_minimum_metrics(self.metrics_switches)
            enforce_minimum_metrics(self.metrics_small_switches)

            for child in list(self.disk_entries.get_children()):
                self.disk_entries.remove(child)

            for p in DEFAULTS.get("bar_metrics_disks", ["/"]):
                self._add_disk_edit_entry_func(p)

            # Reset notification app lists
            limited_apps_list = DEFAULTS.get("limited_apps_history", ["Spotify"])
            limited_apps_text = ", ".join(f'"{app}"' for app in limited_apps_list)
            self.limited_apps_entry.set_text(limited_apps_text)

            ignored_apps_list = DEFAULTS.get("history_ignored_apps", ["Hyprshot"])
            ignored_apps_text = ", ".join(f'"{app}"' for app in ignored_apps_list)
            self.ignored_apps_entry.set_text(ignored_apps_text)

            # Reset monitor selection
            default_monitors = DEFAULTS.get("selected_monitors", [])
            for monitor_name, checkbox in self.monitor_checkboxes.items():
                # If defaults is empty, check all monitors (show on all)
                is_selected = (
                    len(default_monitors) == 0 or monitor_name in default_monitors
                )
                checkbox.set_active(is_selected)

            self._update_panel_position_sensitivity()

            self.selected_face_icon = None
            self.face_status_label.label = ""
            current_face = os.path.expanduser("~/.face.icon")
            try:
                pixbuf = (
                    GdkPixbuf.Pixbuf.new_from_file_at_size(current_face, 64, 64)
                    if os.path.exists(current_face)
                    else None
                )
                if pixbuf:
                    self.face_image.set_from_pixbuf(pixbuf)
                else:
                    self.face_image.set_from_icon_name("user-info", Gtk.IconSize.DIALOG)
            except Exception:
                self.face_image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)

            if self.lock_switch:
                self.lock_switch.set_active(False)
            if self.idle_switch:
                self.idle_switch.set_active(False)
            print("Settings reset to defaults.")
        dialog.destroy()

    def on_close(self, widget):
        if self.application:
            self.application.quit()
        else:
            self.destroy()
