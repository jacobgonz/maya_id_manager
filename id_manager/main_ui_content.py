import maya.cmds as cmds

from PySide import QtCore

import utils


class LayersOptions(object):
    """
    Class to manage the render layers and aov combo

    """
    def __init__(self, ui):
        self.ui = ui
        self.ui_content()

    def ui_content(self):
        """
        Set the ui content

        :return:
        """

        # Fill Render Layers Combo
        self._render_layers_combo()

        # Fill AOV Combo
        self._aov_combo()

        # UI Signals
        self.ui.connect(self.ui.cb_layers,
                        QtCore.SIGNAL("currentIndexChanged(int)"),
                        self._render_layer_switch_callback)

        self.ui.connect(self.ui.cb_AOV,
                        QtCore.SIGNAL("currentIndexChanged(int)"),
                        self._aov_switch_callback)

    def _render_layers_combo(self):
        """
        Set the content for the render layers combo

        :return:
        """

        self.id_layers = utils.get_layers_aovs()

        render_layers = sorted(self.id_layers)
        current_layer = cmds.editRenderLayerGlobals(currentRenderLayer=True,
                                                    query=True)
        if current_layer not in render_layers:
            current_layer_index = 0
        else:
            current_layer_index = render_layers.index(current_layer)

        self.ui.cb_layers.clear()

        self.ui.cb_layers.addItems(render_layers)
        self.ui.cb_layers.setCurrentIndex(current_layer_index)

        return None

    def _aov_combo(self):
        """
        Add the content to the aov combo list

        :return:
        """

        # FIXME: Maya does not recognize AOVs on start up
        if not cmds.objExists("defaultArnoldRenderOptions.displayAOV"):
            return

        current_layer = cmds.editRenderLayerGlobals(currentRenderLayer=True,
                                                    query=True)

        aov_list = self.id_layers.get(current_layer, [])

        current_aov = cmds.getAttr("defaultArnoldRenderOptions.displayAOV")
        if current_aov not in aov_list:
            current_aov = "beauty"

        current_aov = current_aov.replace('aiAOV_', '')

        aov_index = aov_list.index(current_aov)

        self.ui.cb_AOV.clear()

        self.ui.cb_AOV.addItems(aov_list)
        self.ui.cb_AOV.setCurrentIndex(aov_index)

        return None

    def _render_layer_switch_callback(self):
        """
        Render layer switch callback for the render layers combo

        :return:
        """

        self.ui.cb_layers.blockSignals(True)

        render_layer = str(self.ui.cb_layers.currentText())

        cmds.editRenderLayerGlobals(currentRenderLayer=render_layer)

        self.idLayers = utils.get_layers_aovs()
        self._aov_combo()

        self.ui.cb_layers.blockSignals(False)

        return

    def _aov_switch_callback(self):
        """
        Aov switch callback for the aov combo

        :return:
        """

        self.ui.cb_AOV.blockSignals(True)

        user_aov = str(self.ui.cb_AOV.currentText())

        cmds.setAttr('defaultArnoldRenderOptions.displayAOV',
                     user_aov,
                     type='string')

        self.ui.cb_AOV.blockSignals(False)

        return
