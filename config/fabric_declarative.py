import yaml
import gi

gi.require_version("Gtk", "3.0")
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.image import Image as FabricImage
from fabric.widgets.label import Label
from fabric.widgets.scale import Scale
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.stack import Stack
from fabric.widgets.window import Window
from gi.repository import Gtk


class FabricUIBuilder:
    def __init__(self, parent_instance=None):
        """Initialize the builder with optional parent instance for method binding."""
        self.parent = parent_instance
        self.widget_refs = {}
        self.widget_methods = {}

    def create_widget(self, spec):
        """Create a Fabric widget based on the specification."""
        widget_type = spec.get("type")
        props = spec.get("props", {})
        widget_id = spec.get("id")

        # Create the appropriate widget type
        widget = None

        # Fabric widgets
        if widget_type == "Window":
            widget = Window(**props)
        elif widget_type == "Box":
            widget = Box(**props)
        elif widget_type == "Button":
            widget = Button(**props)
        elif widget_type == "Entry":
            widget = Entry(**props)
        elif widget_type == "Label":
            widget = Label(**props)
        elif widget_type == "Scale":
            widget = Scale(**props)
        elif widget_type == "ScrolledWindow":
            widget = ScrolledWindow(**props)
        elif widget_type == "Stack":
            widget = Stack(**props)
        elif widget_type == "FabricImage":
            widget = FabricImage(**props)

        # GTK widgets
        elif widget_type == "Grid":
            widget = Gtk.Grid()
            for prop, value in props.items():
                if prop == "column_spacing":
                    widget.set_column_spacing(value)
                elif prop == "row_spacing":
                    widget.set_row_spacing(value)
                elif prop == "margin_start":
                    widget.set_margin_start(value)
                elif prop == "margin_end":
                    widget.set_margin_end(value)
                elif prop == "margin_top":
                    widget.set_margin_top(value)
                elif prop == "margin_bottom":
                    widget.set_margin_bottom(value)
        elif widget_type == "GtkBox":
            orientation = props.get("orientation", Gtk.Orientation.VERTICAL)
            if isinstance(orientation, str):
                orientation = (
                    Gtk.Orientation.HORIZONTAL
                    if orientation == "horizontal"
                    else Gtk.Orientation.VERTICAL
                )
            widget = Gtk.Box(orientation=orientation)
            if "spacing" in props:
                widget.set_spacing(props["spacing"])
            if "halign" in props:
                widget.set_halign(self._get_gtk_align(props["halign"]))
            if "valign" in props:
                widget.set_valign(self._get_gtk_align(props["valign"]))
        elif widget_type == "Switch":
            widget = Gtk.Switch()
            if "active" in props:
                widget.set_active(props["active"])
            if "tooltip_text" in props:
                widget.set_tooltip_text(props["tooltip_text"])
        elif widget_type == "ComboBoxText":
            widget = Gtk.ComboBoxText()
            if "tooltip_text" in props:
                widget.set_tooltip_text(props["tooltip_text"])
            if "items" in props:
                for item in props["items"]:
                    widget.append_text(item)
            if "active" in props:
                widget.set_active(props["active"])
        elif widget_type == "CheckButton":
            widget = Gtk.CheckButton()
            if "label" in props:
                widget.set_label(props["label"])
            if "active" in props:
                widget.set_active(props["active"])
        elif widget_type == "FileChooserButton":
            action = props.get("action", Gtk.FileChooserAction.OPEN)
            widget = Gtk.FileChooserButton(title=props.get("title", ""), action=action)
            if "filename" in props:
                widget.set_filename(props["filename"])
            if "tooltip_text" in props:
                widget.set_tooltip_text(props["tooltip_text"])
        elif widget_type == "StackSwitcher":
            widget = Gtk.StackSwitcher()
            if "orientation" in props:
                orientation = props["orientation"]
                if isinstance(orientation, str):
                    orientation = (
                        Gtk.Orientation.HORIZONTAL
                        if orientation == "horizontal"
                        else Gtk.Orientation.VERTICAL
                    )
                widget.set_orientation(orientation)

        # Store widget reference if ID is provided
        if widget_id and widget is not None:
            self.widget_refs[widget_id] = widget

        # Process children if any
        children = spec.get("children", [])
        for child_spec in children:
            child_widget = self.create_widget(child_spec)
            if child_widget:
                if widget_type == "Grid" and "grid_position" in child_spec:
                    pos = child_spec["grid_position"]
                    widget.attach(child_widget, pos[0], pos[1], pos[2], pos[3])
                elif hasattr(widget, "add"):
                    widget.add(child_widget)
                elif hasattr(widget, "append"):
                    widget.append(child_widget)

        # Process special properties or actions
        if widget_type == "Stack" and "pages" in spec:
            for page in spec["pages"]:
                page_widget = self.create_widget(page["content"])
                widget.add_titled(page_widget, page["name"], page["title"])
        elif widget_type == "StackSwitcher" and "stack" in spec:
            stack_ref = self.widget_refs.get(spec["stack"])
            if stack_ref:
                widget.set_stack(stack_ref)

        # Connect signals
        signals = spec.get("signals", {})
        for signal_name, handler_info in signals.items():
            if isinstance(handler_info, dict):
                method_name = handler_info.get("method")
                params = handler_info.get("params", {})
                if method_name and self.parent and hasattr(self.parent, method_name):
                    handler = getattr(self.parent, method_name)
                    if params:
                        widget.connect(
                            signal_name,
                            lambda w, *args, h=handler, p=params: h(w, *args, **p),
                        )
                    else:
                        widget.connect(signal_name, handler)
            elif (
                isinstance(handler_info, str)
                and self.parent
                and hasattr(self.parent, handler_info)
            ):
                handler = getattr(self.parent, handler_info)
                widget.connect(signal_name, handler)

        # Store method connections
        methods = spec.get("methods", {})
        for method_name, method_ref in methods.items():
            if widget_id:
                self.widget_methods[(widget_id, method_name)] = method_ref

        return widget

    def _get_gtk_align(self, align_str):
        """Convert string alignment to GTK alignment constant."""
        if align_str == "start":
            return Gtk.Align.START
        elif align_str == "end":
            return Gtk.Align.END
        elif align_str == "center":
            return Gtk.Align.CENTER
        elif align_str == "fill":
            return Gtk.Align.FILL
        return Gtk.Align.START

    def load_from_yaml(self, yaml_file):
        """Load UI definition from a YAML file and create widgets."""
        with open(yaml_file, "r") as f:
            spec = yaml.safe_load(f)
        return self.create_widget(spec)

    def get_widget(self, widget_id):
        """Get a widget by its ID."""
        return self.widget_refs.get(widget_id)

    def get_widgets(self):
        """Get all widget references."""
        return self.widget_refs
