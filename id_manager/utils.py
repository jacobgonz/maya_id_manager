import maya.cmds as cmds

from mtoa import core, aovs


def get_layers_aovs():
    """

    :return: dictionary where keys are render layer and values the aovs
             active on each render layer

    """
    aov_dict = dict()

    render_layers = [x for x in cmds.ls(type="renderLayer") \
                     if "defaultRenderLayer" not in x]

    scene_aovs = filter(lambda x:
                        cmds.attributeQuery('attr_id', n=x, exists=True),
                        cmds.ls(type="aiAOV"))

    for render_layer in render_layers:
        aov_dict[render_layer] = ["beauty"]

        for aov in scene_aovs:
            attr = "enabled"
            layer_overrides = cmds.listConnections("%s.%s" % (aov, attr), plugs=1)

            # Use attribute value if attribute has no overrides on any layer
            value = cmds.getAttr("%s.%s" % (aov, attr))

            if layer_overrides:
                attribute_plug = False
                # Use default Render Layer Value if attr is not overriden for a layer

                for layerOver in layer_overrides:
                    if "defaultRenderLayer" == layerOver.split(".")[0]:
                        attribute_plug = layerOver

                # Query attr Layer Override value
                for layerOver in layer_overrides:
                    if render_layer == layerOver.split(".")[0]:
                        attribute_plug = layerOver

                if not attribute_plug:
                    continue

                values = [False, True]

                value = values[int(cmds.getAttr(attribute_plug.replace("plug", "value")))]

            if value is True:
                aov_dict[render_layer].append(aov.split("aiAOV_")[-1])

    return aov_dict


def id_objects_dict(id_sets):
    """

    :param id_sets: a list of aov names
    :return: dictionary for each aov, their id rgba entries, and the objects
            added to each rgb entry
    """

    attribute_type = "mtoa_constant_"
    id_dict = dict()

    current_layer = cmds.editRenderLayerGlobals(currentRenderLayer=True,
                                                query=True)

    layer_objects = get_render_layer_objects(current_layer) or []

    # Return False if render layer has no members
    layer_objects = [x for x in layer_objects if get_object_primary_visibility(x)] or None

    for idSet in id_sets:
        id_dict[idSet] = {"Red": [],
                          "Green": [],
                          "Blue": [],
                          "Holdout": []
                          }

        if not layer_objects:
            continue

        objects_with_id = []
        id_objects = []

        for object_name in layer_objects:
            shape_node = get_object_shape_node(object_name)
            if shape_node is False:
                continue

            if cmds.nodeType(shape_node) not in render_layer_accepted_objects():
                continue

            else:
                id_objects.append(object_name)

            color_attribute = attribute_type + idSet
            alpha_attribute = "%s_Alpha" % color_attribute

            if cmds.attributeQuery(alpha_attribute, node=shape_node, exists=True):
                attribute_value = cmds.getAttr("%s.%s" % (shape_node, alpha_attribute))[0]

                if "_Alpha" in alpha_attribute and attribute_value == (1, 1, 1):
                    id_dict[idSet]["Alpha"].append(myObj)
                    objects_with_id.append(myObj)

                elif "_Alpha" in alpha_attribute and attribute_value == (-1, -1, -1):
                    id_dict[idSet]["Alpha_Neg"].append(myObj)
                    objects_with_id.append(myObj)

            if cmds.attributeQuery(color_attribute, node=shape_node, exists=True):
                attribute_value = cmds.getAttr("%s.%s" % (shape_node, color_attribute))[0]

                rbg_value = None
                for v in attribute_value:
                    id_colors = ["Red", "Green", "Blue"]
                    if v == 1:
                        rbg_value = id_colors[attribute_value.index(v)]
                    elif v == -1:
                        rbg_value = "%s_Neg" % id_colors[attribute_value.index(v)]

                if rbg_value is not None:
                    id_dict[idSet][rbg_value].append(myObj)
                    objects_with_id.append(myObj)

        id_dict[idSet]["Holdout"] = filter(lambda x: x not in objects_with_id, id_objects)

    return id_dict


def set_attribute_id(object_name, id_set, id_color):
    """

    :param object_name: the name of a maya node as a string
    :param id_set: the name of an aov as a string
    :param id_color: tje name of an aov's rgb color as a string
    :return:
    """

    shape_node = cmds.listRelatives(object_name,
                                    allDescendents=True,
                                    fullPath=True,
                                    shapes=True)[0]

    id_color = id_color.split("_Neg")[0]

    channel_values = ["Red_", "Green_", "Blue_"]
    channels = ["", "_Alpha"]

    for ch in channels:
        myAttr = "mtoa_constant_%s%s" % (id_set, ch)

        # Add ID Attribute if not exist
        if not cmds.attributeQuery(myAttr, node=shape_node, exists=True):
            cmds.addAttr(shape_node, ln=myAttr, nn=id_set + ch, uac=1, at="float3")
            for c in channel_values:
                cmds.addAttr(shape_node, ln=c + id_set + ch, at="float", p=myAttr)

        # Create a layer Override for all attributes
        cmds.editRenderLayerAdjustment("%s.%s" % (shape_node, myAttr))

        # Set all values to 0:
        cmds.setAttr("%s.%s" % (shape_node, myAttr), 0, 0, 0, type="double3")
        if id_color == "Holdout":
            continue

        # Set Id Color as per user input
        if id_color in ch and id_color == "Alpha":
            cmds.setAttr("%s.%s" % (shape_node, myAttr), 1, 1, 1, type="double3")

        if id_color not in ch and ch != "_Alpha":
            cmds.setAttr("%s.%s" % (shape_node, myAttr),
                         int(id_color in channel_values[0]),
                         id_color in channel_values[1],
                         id_color in channel_values[2])

    return


def create_new_aov(aov_name):
    """

    :param aov_name: name of the aov to create as a string
    :return: object name of the aov created as a string
    """

    scene_aovs = [x for x in cmds.ls(type="aiAOV")]
    ai_aov = "aiAOV_%s" % aov_name

    if ai_aov in scene_aovs:
        print "%s already exists in the scene" % aov_name
        return False

    new_aov = aovs.AOVInterface()

    data_type = "rgb"
    new_aov.addAOV(aov_name, data_type)

    # Set AOV disabled
    cmds.setAttr("%s.enabled" % ai_aov, 0)

    return ai_aov


def create_connect_aov_shader(aov_name):
    """

    :param aov_name: the name of an aov object as a string
    :return: the name of the created surface shader as a string
    """

    surface_shader = cmds.shadingNode("surfaceShader",
                                      name="AOV_%s_MAT" % aov_name,
                                      asShader=True)

    # Create a Shading Group so Miasma will publish this shader
    shading_group = cmds.createNode("shadingEngine",
                                    name="AOV_%s_SG" % aov_name)

    cmds.connectAttr("%s.outColor" % surface_shader,
                     "%s.surfaceShader" % shading_group)

    rgb_data = cmds.shadingNode("aiUserDataColor",
                                asShader=True,
                                name="userData_%s" % aov_name)

    cmds.setAttr("%s.colorAttrName" % rgb_data,
                 aov_name,
                 type="string")

    cmds.connectAttr("%s.outColor" % rgb_data,
                     "%s.outColor" % surface_shader,
                     force=True)

    cmds.connectAttr("%s.outColor" % surface_shader,
                     "aiAOV_%s.defaultValue" % aov_name,
                     force=True)

    # Add the attr_id to be identified as an attr id aov type
    cmds.addAttr('aiAOV_%s' % aov_name,
                 ln='attr_id',
                 at='bool',
                 hidden=True)

    return surface_shader


def create_arnold_options():
    core.createOptions()

    return


def select_objects(items):
    """

    :param items: list of objects to select
    :return:
    """

    cmds.select(items)

    return


def object_exists(obj_name):
    return cmds.objExists(obj_name)


def get_object_shape_node(node):
    """

    :param node: the name of a node as a string
    :return: the name of the shape node as a string
    """

    shape_nodes = cmds.listRelatives(node,
                                     allDescendents=True,
                                     fullPath=True,
                                     shapes=True) or []

    if not len(shape_nodes):
        return False

    shape_node = shape_nodes[0]

    return shape_node


def get_object_short_name(node):
    """

    :param node: the long name of an object as a string
    :return:
    """

    short_name = node.split("|")[-1]
    return short_name


def render_layer_accepted_objects():
    """

    :return: a list of the object types accepted as render objects by the id manager
    """

    accepted_objects = ["mesh",
                        "xgmDescription",
                        "pgYetiMaya",
                        "aiStandIn",
                        "pgYetiGroom",
                        "aiVolume"]

    return accepted_objects


def get_render_layer_objects(render_layer):
    """

    :param render_layer: the name a render layer as a string
    :return: a list of the render layers transform nodes
    """

    layer_objects = list(set(cmds.editRenderLayerMembers(render_layer, q=True, fullNames=True) or [])) or None

    if layer_objects is None:
        return False

    layer_transform_nodes = []

    for node in layer_objects:
        if cmds.nodeType(node) != "transform":
            transform_node = cmds.listRelatives(node, parent=True, fullPath=True)
            if transform_node and transform_node[0] not in layer_transform_nodes:
                layer_transform_nodes.append(transform_node[0])
        else:
            if node not in layer_transform_nodes:
                layer_transform_nodes.append(node)

    return layer_transform_nodes


def get_object_primary_visibility(node):
    """

    :param node: the name of a transform node as a string
    :return: a bool for the node primary visibility value
    """

    override = "primaryVisibility"

    if cmds.nodeType(node) == "mesh":
        shape_node = node
    else:
        shape_node = get_object_shape_node(node)

    if shape_node is False:
        return False

    if not cmds.attributeQuery(override, node=shape_node, exists=True):
        return False

    if cmds.getAttr("%s.%s" % (shape_node, override)) is False:
        return False

    object_sets = cmds.listSets(object=node) or False

    if not object_sets:
        return True

    for object_set in object_sets:
        if not cmds.attributeQuery(override, node=object_set, exists=True):
            continue

        if cmds.getAttr("%s.%s" % (object_set, override)) is False:
            return False

    return True
