# Copyright (C) 2008 One Laptop Per Child
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from gettext import gettext as _

import gobject
import gtk

from sugar.graphics import style
from sugar.graphics import iconentry
from sugar.graphics.palette import Palette
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.radiotoolbutton import RadioToolButton

from view.home import favoritesview
from view.home.activitieslist import ActivitiesList

_FAVORITES_VIEW = 0
_LIST_VIEW = 1

_AUTOSEARCH_TIMEOUT = 1000

class HomeBox(gtk.VBox):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self):
        gobject.GObject.__init__(self)

        self._favorites_view = favoritesview.FavoritesView()
        self._list_view = ActivitiesList()
        self._enable_xo_palette = False

        self._toolbar = HomeToolbar()
        self._toolbar.connect('query-changed', self.__toolbar_query_changed_cb)
        self._toolbar.connect('view-changed', self.__toolbar_view_changed_cb)
        self.pack_start(self._toolbar, expand=False)
        self._toolbar.show()

        self._set_view(_FAVORITES_VIEW, favoritesview.RANDOM_LAYOUT)

    def __toolbar_query_changed_cb(self, toolbar, query):
        if self._list_view is None:
            return
        query = query.lower()
        self._list_view.set_filter(query)

    def __toolbar_view_changed_cb(self, toolbar, view, layout):
        self._set_view(view, layout)

    def _set_view(self, view, layout):
        if view == _FAVORITES_VIEW:
            if self._list_view in self.get_children():
                self.remove(self._list_view)

            self._favorites_view.layout = layout

            if self._enable_xo_palette:
                self._favorites_view.enable_xo_palette()

            if self._favorites_view not in self.get_children():
                self.add(self._favorites_view)
                self._favorites_view.show()
        elif view == _LIST_VIEW:
            if self._favorites_view in self.get_children():
                self.remove(self._favorites_view)

            self.add(self._list_view)
            self._list_view.show()
        else:
            raise ValueError('Invalid view: %r' % view)

    _REDRAW_TIMEOUT = 5 * 60 * 1000 # 5 minutes

    def resume(self):
        pass

    def suspend(self):
        pass

    def has_activities(self):
        # TODO: Do we need this?
        #return self._donut.has_activities()
        return False

    def enable_xo_palette(self):
        self._enable_xo_palette = True
        if self._favorites_view is not None:
            self._favorites_view.enable_xo_palette()

class HomeToolbar(gtk.Toolbar):
    __gtype_name__ = 'SugarHomeToolbar'

    __gsignals__ = {
        'query-changed': (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([str])),
        'view-changed':  (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([object, object]))
    }

    def __init__(self):
        gtk.Toolbar.__init__(self)

        self._query = None
        self._autosearch_timer = None

        self._add_separator()

        tool_item = gtk.ToolItem()
        self.insert(tool_item, -1)
        tool_item.show()

        self._search_entry = iconentry.IconEntry()
        self._search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                              'system-search')
        self._search_entry.add_clear_button()
        self._search_entry.set_width_chars(25)
        self._search_entry.connect('activate', self.__entry_activated_cb)
        self._search_entry.connect('changed', self.__entry_changed_cb)
        tool_item.add(self._search_entry)
        self._search_entry.show()

        self._add_separator(expand=True)

        favorites_button = FavoritesButton()
        favorites_button.connect('toggled', self.__view_button_toggled_cb,
                                 _FAVORITES_VIEW)
        self.insert(favorites_button, -1)
        favorites_button.show()

        list_button = RadioToolButton(named_icon='view-list')
        list_button.props.group = favorites_button
        list_button.props.tooltip = _('List view')
        list_button.props.accelerator = _('<Ctrl>L')
        list_button.connect('toggled', self.__view_button_toggled_cb,
                            _LIST_VIEW)
        self.insert(list_button, -1)
        list_button.show()

        self._add_separator()

    def __view_button_toggled_cb(self, button, view):
        if button.props.active:
            if view == _FAVORITES_VIEW:
                self.emit('view-changed', view, button.layout)
            else:
                self.emit('view-changed', view, None)
            
    def _add_separator(self, expand=False):
        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.GRID_CELL_SIZE,
                                       style.GRID_CELL_SIZE)
        self.insert(separator, -1)
        separator.show()

    def __entry_activated_cb(self, entry):
        if self._autosearch_timer:
            gobject.source_remove(self._autosearch_timer)
        new_query = entry.props.text
        if self._query != new_query:
            self._query = new_query
            self.emit('query-changed', self._query)

    def __entry_changed_cb(self, entry):
        if not entry.props.text:
            entry.activate()
            return

        if self._autosearch_timer:
            gobject.source_remove(self._autosearch_timer)
        self._autosearch_timer = gobject.timeout_add(_AUTOSEARCH_TIMEOUT,
                                                     self.__autosearch_timer_cb)

    def __autosearch_timer_cb(self):
        self._autosearch_timer = None
        self._search_entry.activate()
        return False

class FavoritesButton(RadioToolButton):
    __gtype_name__ = 'SugarFavoritesButton'
    
    def __init__(self):
        RadioToolButton.__init__(self)

        self.props.named_icon = 'view-radial'
        self.props.tooltip = _('Favorites view')
        self.props.accelerator = _('<Ctrl>R')
        self.props.group = None

        self._layout = favoritesview.RANDOM_LAYOUT

        # TRANS: label for the free layout in the favorites view
        menu_item = MenuItem(_('Free'), 'activity-start')
        menu_item.connect('activate', self.__layout_activate_cb,
                          favoritesview.RANDOM_LAYOUT)
        self.props.palette.menu.append(menu_item)
        menu_item.show()

        # TRANS: label for the ring layout in the favorites view
        menu_item = MenuItem(_('Ring'), 'view-radial')
        menu_item.connect('activate', self.__layout_activate_cb,
                          favoritesview.RING_LAYOUT)
        self.props.palette.menu.append(menu_item)
        menu_item.show()

    def __layout_activate_cb(self, menu_item, layout):
        if self._layout == layout and self.props.active:
            return
        elif self._layout != layout:
            if layout == favoritesview.RANDOM_LAYOUT:
                self.props.named_icon = 'activity-start'
            elif layout == favoritesview.RING_LAYOUT:
                self.props.named_icon = 'view-radial'
            else:
                raise ValueError('Invalid layout: %r' % layout)
            self._layout = layout
        if not self.props.active:
            self.props.active = True
        else:
            self.emit('toggled')

    def _get_layout(self):
        return self._layout
    layout = property(_get_layout, None)

