"""
Add apertures to a Pollination Room given a ratio of aperture area to face area.
"""

# import rhinocommon
import Rhino

# import pollination part
import clr
clr.AddReference('Share.dll')
clr.AddReference('HoneybeeSchema.dll')
import System.Guid
import HoneybeeSchema as HB # csharp version of HB Schema
import Share as SH # It contains Pollination RhinoObject classes
import Share.Convert as CO # It contains utilities to convert RhinoObject <> HB Schema

# STRATEGY
# Pollination rooms > JSON > Honeybee rooms > JSON > Pollination rooms

# SELECTION PART
#---------------------------------------------------------------------------------------------#
# doc info
doc = Rhino.RhinoDoc.ActiveDoc
tol = doc.ModelAbsoluteTolerance
a_tol = doc.ModelAngleToleranceRadians
current_model = SH.Entity.ModelEntityTable.Instance.CurrentModelEntity

# start the command
go = Rhino.Input.Custom.GetObject()

# set the selection
go.SetCommandPrompt('Please select pollination rooms')
go.GeometryFilter = Rhino.DocObjects.ObjectType.Brep
go.GroupSelect = False
go.SubObjectSelect = False
go.AcceptNothing(True)
go.GetMultiple(0, 0)

# filter by rooms
rooms = [_.Object() for _ in go.Objects() if isinstance(_.Object(), SH.Objects.RoomObject)]

if not rooms:
    raise ValueError('Please, select pollination rooms')

# HONEYBEE PART
#---------------------------------------------------------------------------------------------#
try:  # import dependencies
    import json
    import honeybee.dictutil as hb_dict_util
    from honeybee.boundarycondition import Outdoors
    from honeybee.facetype import Wall
    from ladybug_geometry.geometry3d.face import Face3D
    from ladybug_rhino.fromgeometry import from_face3d
    from honeybee.orientation import check_matching_inputs, angles_from_num_orient, \
    inputs_by_index, face_orient_index
except ImportError as e:
    raise ImportError('\nFailed to import:\n\t{}'.format(e))

def can_host_apeture(face):
    return isinstance(face.boundary_condition, Outdoors) and \
        isinstance(face.type, Wall)

def create_brep_from_ratio(all_inputs, subdivide, angles, face):
    tolerance = 0.01
    breps = []
    if can_host_apeture(face):
        orient_i = face_orient_index(face, angles)
        rat, hgt, sil, hor, vert = inputs_by_index(orient_i, all_inputs)
        if not rat: return breps
        face3ds = None

        if subdivide:
            face3ds = face.geometry.sub_faces_by_ratio_sub_rectangle(rat, hgt, sil, hor, vert, tolerance)
        else:
            face3ds = face.geometry.sub_faces_by_ratio_rectangle(rat, tolerance)
        if not face3ds: return

        for geo in face3ds:
            brep = from_face3d(geo)
            #brep.UserDictionary.Set('FaceIdentifier', face.identifier)
            breps.append(brep)

        return breps

def get_aperture_brep_from_json_room(hb_json, ratio, win_height, sill_height, horiz_separ, vertical_separ, subdivide = False):
    # create objects first
    hb_dict = json.loads(hb_json)
    hb_obj = hb_dict_util.dict_to_object(hb_dict, False)
    if not hb_obj: raise ValueError(e)
    
    # duplicate the initial objects
    hb_obj = hb_obj.duplicate()
    
    # set defaults for any blank inputs
    #conversion = conversion_to_meters()
    _win_height_ = [win_height]
    _sill_height_ = [sill_height]
    _horiz_separ_ = [horiz_separ]
    vert_separ_ = [vertical_separ]
    
    # gather all of the inputs together
    all_inputs = [ratio, _win_height_, _sill_height_, _horiz_separ_,
                  vert_separ_]
    
    all_inputs, num_orient = check_matching_inputs(all_inputs)
    angles = angles_from_num_orient(num_orient)
    
    apertures = []
    for face in hb_obj.faces:
        brep = create_brep_from_ratio(all_inputs, subdivide, angles, face)
        if brep:
            apertures.extend(brep)
    return apertures

# GO BACK TO POLLINATION RHINO
#---------------------------------------------------------------------------------------------#
# TODO: Fix the model panel issue

ratio = [0.2, 0.2, 0.2, 0.2]

for rm in rooms:
    json_room = rm.ToHBObject().ToJson()
    breps = get_aperture_brep_from_json_room(json_room, ratio, 2, 0.6, 2, 0, True)
    
    apertures = []
    for brp in breps:
        apt = SH.Objects.ApertureObject(brp)
        apt.Id = System.Guid.NewGuid()
        apertures.append(apt)
    
    new_room, added_apts = rm.AddApertures(apertures, tol, a_tol)
    if not added_apts: continue
    
    for apt in added_apts:
        doc.Objects.AddRhinoObject(apt)
    
    doc.Objects.Replace(Rhino.DocObjects.ObjRef(rm.Id), new_room)

doc.Views.Redraw()