import os

from PySide import QtGui, QtCore

import utils

reload(utils)


class ElementItem(QtGui.QTreeWidgetItem):
    """
    Tree Widget Item class used for objects added to the id colors

    """

    def __init__(self, name, parent):
        QtGui.QTreeWidgetItem.__init__(self, parent)

        short_name = utils.get_object_short_name(name)
        self.setText(0, short_name)

        font = QtGui.QFont()
        font.setPointSize(10)

        self.setFont(0, font)
        self.setData(0, QtCore.Qt.UserRole, "object")
        self.setData(1, QtCore.Qt.UserRole, name)


class ElementGroupItem(QtGui.QTreeWidgetItem):
    """
    Tree Widget Item class used for the id color parents

    """

    def __init__(self, name, parent, tree):
        QtGui.QTreeWidgetItem.__init__(self, parent)

        self.tree = tree

        self.color_button = QtGui.QPushButton(name, self.tree)

        button_colors = {"Alpha": "#666666",
                         "Red": "#ff0000",
                         "Green": "#097709",
                         "Blue": "#0000ff",
                         "Holdout": "#000000",
                         "Alpha_Neg": "#888888",
                         "Red_Neg": "#ff2222",
                         "Green_Neg": "#099909",
                         "Blue_Neg": "#3333ff"
                         }

        self.color_button.setFixedSize(70, 20)
        self.color_button.setStyleSheet("background-color: %s"
                                        % button_colors.get(name, "#52869e"))

        self.setData(0, QtCore.Qt.UserRole, "color")
        self.setData(1, QtCore.Qt.UserRole, name)

        self.tree.setItemWidget(self, 0, self.color_button)


class IdSetTreeView(QtGui.QTreeWidget):
    """
    Tree view for the id set found
    Includes the each id set colors and the objects added to each color

    """

    def __init__(self, aov_list, parent=None):
        super(IdSetTreeView, self).__init__(parent)

        self.aov_list = aov_list

        self.ui = parent
        self.items_dict = dict()

        self.selectSignalBlocked = False

        self.setDragDropMode(QtGui.QAbstractItemView.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.IgnoreAction)

        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        self.headerItem().setText(0, "ID SETS")

        if self.aov_list is None:
            return

        self.scnData = utils.id_objects_dict(self.aov_list)

        self._ui_content()

        selection_model = self.selectionModel()
        selection_model.selectionChanged.connect(self._select_scene_objects)

    def _ui_content(self):
        """
        Set the ui content

        :return:
        """

        # Cleat the tree
        self.clear()

        # Set the font
        font = QtGui.QFont()
        font.setPointSize(11)

        # Add the id sets and set items
        for id_set, id_dict in sorted(self.scnData.items()):
            tree_item = QtGui.QTreeWidgetItem(self)

            tree_item.setText(0, id_set)
            tree_item.setFont(0, font)

            icon_folder = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(icon_folder, "icons", "IdSet.png")

            tree_item.setIcon(0, QtGui.QIcon(icon_path))

            tree_item.setData(0, QtCore.Qt.UserRole, "set")
            tree_item.setData(1, QtCore.Qt.UserRole, id_set)

            for id_color, id_objects in sorted(id_dict.items()):
                if id_color != "Holdout":
                    self._add_id_color(id_objects,
                                       id_color,
                                       tree_item)

            self._add_id_color(id_dict["Holdout"], "Holdout", tree_item)

        return

    def _add_id_color(self, id_objects, id_color, parent):
        """

        Add the id color and the objects items for this color

        :param id_objects: objects to be added to the id_color
        :type id_objects: list
        :param id_color: id_color name
        :type id_color: string
        :param parent: tree widget item parent
        :return:
        """

        id_item = ElementGroupItem(id_color, parent, self)
        id_item.color_button.clicked.connect(lambda: self._add_items_to_color(id_item))

        for obj in id_objects:
            object_item = ElementItem(obj, id_item)

            if self.items_dict.get(obj, None) is None:
                self.items_dict[obj] = {parent: object_item}
            else:
                self.items_dict[obj][parent] = object_item

        return

    def dragEnterEvent(self, event):
        """
        PySide drag enter event

        :param event:
        :return:
        """

        selected_items = [x for x in self.selectedItems() \
                          if x.data(0, QtCore.Qt.UserRole) == "object"] or None

        if selected_items is None:
            event.ignore()
            return

        event.accept()

    def dropEvent(self, event):
        """
        PySide drop event to move items between the id colors

        :param event:
        :return:
        """

        # Get the id color to drop the items into
        drop_id_color = self.itemAt(event.pos())
        drop_id_color = self.invisibleRootItem() if drop_id_color is None else drop_id_color

        # If the drop position is not valid we pass
        if drop_id_color is None:
            event.ignore()
            return

        # If the drop position is not an id color item we pass
        if drop_id_color.data(0, QtCore.Qt.UserRole) != "color":
            event.ignore()
            return

        # Get the drop items - the selected tree items
        drop_items = [x for x in self.selectedItems()
                      if x.data(0, QtCore.Qt.UserRole) == "object"] or None

        # If not items selected we pass
        if drop_items is None:
            event.ignore()
            return

        # Drop the items into the new tree parent
        self._drop_tree_items(drop_items, drop_id_color)

        event.accept()

        return None

    def _drop_tree_items(self, drop_items, drop_id_color):
        """
        Drop tree widget items to a new parent

        :param drop_items: list of tree items to drop
        :param drop_id_color: tree widget item to drop into
        :return:
        """

        # Block the selection signals while we process the drop
        self.selectSignalBlocked = True

        # Get the drop id color parent - the aov id tree widget item
        drop_id_set = drop_id_color.parent()

        # Drop the items into the new parent
        for item in drop_items:
            if item.parent().parent().text(0) != drop_id_color.parent().text(0):
                drop_items.remove(item)
            else:
                item.parent().removeChild(item)

                drop_id_color.insertChildren(0, drop_items)

        # Set the items as selected
        for item in drop_items:
            item.setSelected(True)

            # Set new idColor - need to optimize!
            utils.set_attribute_id(item.data(1, QtCore.Qt.UserRole),
                                   drop_id_set.data(1, QtCore.Qt.UserRole),
                                   drop_id_color.data(1, QtCore.Qt.UserRole))

        # Set the new parent as expanded so we can see the dropped items
        drop_id_color.setExpanded(True)

        # Unblock the selection change signals
        self.selectSignalBlocked = False

        return None

    def _add_items_to_color(self, drop_id_color):
        """
        Update the drop id color tree item's list

        :param drop_id_color: tree widget item for the drop id color
        :return:
        """

        # Get the drop item names
        drop_names = [x.data(1, QtCore.Qt.UserRole) for x in self.selectedItems()
                      if x.data(0, QtCore.Qt.UserRole) == "object"] or None

        # If no drop items return
        if drop_names is None:
            return

        # Get the tree widget items for the drop names
        drop_list = [self.items_dict[drop_name][drop_id_color.parent()] for drop_name in list(set(drop_names))]

        # Update the id color tree widget content list
        self._drop_tree_items(drop_list, drop_id_color)

        return None

    def _select_scene_objects(self):
        """
        Select the maya objects for the tree selected items

        :return:
        """

        # Skip if the selection signals have been blocked
        if self.selectSignalBlocked:
            return

        # Get the tree selected items which exist inside the maya scene
        selected_items = [x.data(1, QtCore.Qt.UserRole) for x in self.selectedItems()
                         if utils.object_exists(str(x.text(0)))] or None

        # If not valid items selected we pass
        if selected_items is None:
            return

        # Select the maya scene objects
        utils.select_objects(selected_items)

        return None
