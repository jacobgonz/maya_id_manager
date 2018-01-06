import os

from PySide import QtGui, QtCore

import maya.cmds as cmds
import maya.OpenMaya as api

import utils
import pyside_util

import main_ui
import main_ui_content
import id_set_tree

reload(main_ui)
reload(main_ui_content)
reload(id_set_tree)

reload(utils)
reload(pyside_util)


class IdDialog(QtGui.QDialog, main_ui.Ui_Form):
    def __init__(self, parent=None):
        super(IdDialog, self).__init__(parent)
        self.setupUi(self)

        self.aov_tree_list = None

        # Set Window Flags
        pyside_util.set_linux_window_flags(self)

        self._ui_content()

    def _ui_content(self):
        """
        Set the ui content

        :return:
        """

        # Add the render layers drop down combo
        self.layer_options = main_ui_content.LayersOptions(self)

        # Add the aov ui content
        self._aov_content()

        # Ui signals
        self.btn_newId.clicked.connect(self._create_aov)

        self.cb_layers.currentIndexChanged.connect(self._aov_content)

        self.aov_tree_list.itemExpanded.connect(self._selection_update)

        self.btn_refresh.clicked.connect(self._refresh_content)

        # Maya selection changed callback
        self._register_selection_callback()

        # Refresh button Icons
        icon_folder = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(icon_folder, "icons", "refresh.png")

        self.btn_refresh.setIcon(QtGui.QIcon(icon_path))

        return

    def _aov_content(self):
        """
        Add the aov content to the id sets tree

        :return:
        """

        # Remove the widget if it has been added before
        if self.aov_tree_list is not None:
            self.lyAovList.removeWidget(self.aov_tree_list)

        # Gather the aov list - exclude the beauty aov
        aov_list = [self.cb_AOV.itemText(i) for i in range(self.cb_AOV.count())
                    if self.cb_AOV.itemText(i) != "beauty"] or None

        # Add the aov id sets content
        self.aov_tree_list = id_set_tree.IdSetTreeView(aov_list, parent=self)
        self.lyAovList.addWidget(self.aov_tree_list)

        return

    def _refresh_content(self):
        """
        Refresh the ui content callback

        :return:
        """

        self.cb_layers.blockSignals(True)

        # FIXME: Maya does not recognize new AOVS until render layer switch
        # Switch to master layer and back to force refresh
        # Need tp fix this
        user_layer = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)

        cmds.editRenderLayerGlobals(currentRenderLayer="defaultRenderLayer")
        cmds.editRenderLayerGlobals(currentRenderLayer=user_layer)

        self.layer_options.ui_content()

        self.cb_layers.blockSignals(False)

        self._aov_content()

        return

    def _create_aov(self):
        """
        Create a new aov callback

        :return:
        """

        aov_name = self.le_idName.text()

        if not ("aiAOV_%s" % aov_name) in cmds.ls(type="aiAOV"):
            utils.create_new_aov(aov_name)

        # Enable AOV on current layer as override
        render_layer = cmds.editRenderLayerGlobals(query=True, crl=True)

        cmds.editRenderLayerAdjustment("aiAOV_%s.enabled" % aov_name,
                                       layer=render_layer)

        cmds.setAttr("aiAOV_%s.enabled" % aov_name, 1)

        utils.create_connect_aov_shader(aov_name)

        self._refresh_content()

        return

    def _selection_update(self):
        """
        Update the ui against the new objects scene selection

        :return:
        """

        # Get the ui selected items if the exist in the maya scene
        selected_items = [x.data(1, QtCore.Qt.UserRole)
                          for x in self.aov_tree_list.selectedItems()
                          if cmds.objExists(str(x.text(0)))] or []

        # Get all tree items
        tree_items = set(self.aov_tree_list.items_dict.keys())

        # Get the current scene selection
        scene_selection = cmds.ls(sl=True, long=True) or []

        # Get the valid selected items - items selected in the maya scene which are
        # added to the tree
        valid_selection = [x for x in scene_selection if x in tree_items] or None

        # If we don't have a valid selection list clear the tree selection
        if valid_selection is None:
            self.aov_tree_list.clearSelection()
            return None

        # If the valid selection list equals the scene selected items pass
        if set(selected_items) == set(valid_selection):
            return None

        # Block the selection update signal
        self.aov_tree_list.selectSignalBlocked = True

        # Clear the tree selection
        self.aov_tree_list.clearSelection()

        # Select all tree items in the valid selection list
        for item in valid_selection:
            for parent, treeItem in self.aov_tree_list.items_dict[item].iteritems():
                if parent is not None and parent.isExpanded():
                    treeItem.setSelected(True)

        # Unblock the selection update signals
        self.aov_tree_list.selectSignalBlocked = False

        return None

    def _update_selection_callback(self, *args):
        """
        Callback for updating the ui contents on scene selection changed

        :param args:
        :return:
        """

        self._selection_update()
        return

    def _register_selection_callback(self):
        """
        Register the maya selection changed callback

        :return:
        """

        self._selection_changed_callback_active = True
        self._selection_changed_callback = api.MEventMessage.addEventCallback("SelectionChanged",
                                                                              self._update_selection_callback)
        return

    def _deregister_selection_callback(self):
        """
        Deregister the maya selection changed callback

        :return:
        """

        if self._selection_changed_callback_active:
            api.MMessage.removeCallback(self._selection_changed_callback)
            self._selection_changed_callback_active = False

        return

    def closeEvent(self, event):
        """
        PySide close event used to deregister the selection update callback on ui closes

        :param event:
        :return:
        """

        self._deregister_selection_callback()

        return

    def keyPressEvent(self, event):
        """
        PySide keyPressEvent used to keep focus on the ui on key press
        Workaround to stop Maya from stealing focus

        :param event:
        :return:
        """

        if event.key() in (QtCore.Qt.Key_Shift,
                           QtCore.Qt.Key_Control,
                           QtCore.Qt.Key_CapsLock):
            event.accept()
        else:
            event.ignore()

        return None


def main():
    """
    Main entry point for the script

    :return:
    """

    # Get the current layer
    current_layer = cmds.editRenderLayerGlobals(query=True, crl=True)

    # If we are on the default layer we don't launch the UI
    if current_layer == "defaultRenderLayer":
        warning = "ID Manager cannot be used on the Master Render Layer"
        pyside_util.display_message_box("ID Tree Manager", warning)
        return False

    # If the render engine is not set to Arnold we don't launch the UI
    if cmds.getAttr('defaultRenderGlobals.currentRenderer') != 'arnold':
        warning = "Arnold is not set as scene render engine"
        pyside_util.display_message_box("ID Tree Manager", warning)
        return False

    # Create arnold options before loading the UI
    utils.create_arnold_options()

    # Launch the Id Manager Dialog
    parent = pyside_util.get_maya_window_by_name("idManagerTree_ui")
    ui = IdDialog(parent=parent)
    ui.show()

    return


if __name__ == '__main__':
    main()