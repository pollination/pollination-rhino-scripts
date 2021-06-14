"""
Select all apertures of Pollination Rooms, get the WWR and change it.
-
It shows the relative % of apertures and the total % of apertures on facade by orientation
"""

# import rhinocommon
import Rhino
import System
import Rhino.UI
import Eto.Drawing as drawing
import Eto.Forms as forms

# import pollination part
import clr
clr.AddReference('Pollination.Core.dll')
clr.AddReference('HoneybeeSchema.dll')
import System.Guid
import HoneybeeSchema as hb # csharp version of HB Schema
import Core as sh # It contains Pollination RhinoObject classes
import Core.Convert as co # It contains utilities to convert RhinoObject <> HB Schema
from Core.Entity import EntityHelper
from System.Collections.Generic import List

# Pollination Rhino Plugin is inside rhp
PollinationRhinoPlugIn = Rhino.PlugIns.PlugIn.Find(System.Guid("8b32d89c-3455-4c21-8fd7-7364c32a6feb"))

# STRATEGY
# Pollination rooms > JSON > Honeybee rooms > JSON > Pollination rooms

# SELECTION PART
#---------------------------------------------------------------------------------------------#
# doc info
doc = Rhino.RhinoDoc.ActiveDoc
tol = doc.ModelAbsoluteTolerance
a_tol = doc.ModelAngleToleranceRadians
current_model = sh.Entity.ModelEntityTable.Instance.CurrentModelEntity
doc_unit = Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem

# get all objects
objects = Rhino.RhinoDoc.ActiveDoc.Objects

# filter by rooms
rooms = [_ for _ in objects if isinstance(_, sh.Objects.RoomObject)]

if not rooms:
    raise ValueError('No rooms found.')

# HONEYBEE PART
#---------------------------------------------------------------------------------------------#
try:  # import dependencies
    import json
    from itertools import groupby
    import honeybee.dictutil as hb_dict_util
    from honeybee.boundarycondition import Outdoors
    from honeybee.facetype import Wall
    from ladybug_geometry.geometry3d.face import Face3D
    from ladybug_rhino.fromgeometry import from_face3d
    from honeybee.orientation import check_matching_inputs, angles_from_num_orient, \
    inputs_by_index, face_orient_index
except ImportError as e:
    raise ImportError('\nFailed to import:\n\t{}'.format(e))

def is_outdoor_and_wall(face):
    return isinstance(face.boundary_condition, Outdoors) and \
        isinstance(face.type, Wall)

def has_aperture(face):
    if face.apertures: 
        return True
    return False

def divide_by_orientation(angles, face):
    if is_outdoor_and_wall(face):
        orient_i = face_orient_index(face, angles)
        out_face = (orient_i, face)
        
        return out_face

def create_brep_from_ratio(face, rat):
    breps = []
    if is_outdoor_and_wall(face) and has_aperture(face):
        face3ds = face.geometry.sub_faces_by_ratio_rectangle(rat, tol)
        if not face3ds: return
        
        for geo in face3ds:
            brep = from_face3d(geo)
            breps.append(brep)
    return breps

def get_faces_group_by_orientation(hb_rooms, num_orient=4):
    # duplicate the initial objects
    hb_objs = [obj.duplicate() for obj in hb_rooms]
    
    # get a list of angles used to categorize the faces
    angles = angles_from_num_orient(num_orient)
    
    # loop through the input objects and add apertures
    aperture_geometries = []
    for obj in hb_objs:
        apertures = []
        for face in obj.faces:
            brep = divide_by_orientation(angles, face)
            if brep:
                apertures.append(brep)
        
        aperture_geometries.extend(apertures)
    
    # sort the apertures
    aperture_geometries = sorted(aperture_geometries)
    apt_iterator = groupby(aperture_geometries, lambda _: _[0])
    
    # get faces with apertures by orientation
    group_faces = []
    group_angles = []
    for key, group in apt_iterator:
        group_faces.append([_[1] for _ in group])
        group_angles.append(angles[key])
    
    return group_faces

def get_current_wwr(group_faces, overall = False):
    # N E S W
    in_ratios = []
    
    for faces in group_faces:
        face_apt_area = []
        face_wall_area = []
        ratio = 0
        
        for face in faces:
            if not has_aperture(face) and not overall:
                continue
            face_wall_area.append(face.area)
            face_apt_area.append(face.aperture_area)
        
        aperture_area = sum(face_apt_area)
        wall_area = sum(face_wall_area)
        
        # avoid divided by 0
        if not wall_area:
            wall_area = 1
        ratio = round(aperture_area / wall_area, 2)
        
        in_ratios.append(ratio)
    return in_ratios

def get_aperture_breps(group_faces, in_ratio, out_ratio):
    breps = []
    for i, faces in enumerate(group_faces):
        apertures = []
        if in_ratio[i] == 0:#or in_ratio[i] == out_ratio[i]:
            continue
        
        for face in faces:
            brep = create_brep_from_ratio(face, out_ratio[i])
            if brep:
                apertures.extend(brep)
        breps.extend(apertures)
    
    return breps

# define Eto window
class RatioSelection(forms.Dialog[list]):
    
    def __init__(self, in_ratio, overall_ratio):
        self.Title = 'WWR Editor'
        self.Resizable = True
        self.Width = 400
        
        min_v = 0
        max_v = 95
        
        in_ratio = map(lambda n: int(n * 100), in_ratio)
        overall_ratio = map(lambda n: int(n * 100), overall_ratio)
        
        self.m_n_label = forms.Label(Text = 'North: rel. {}%   tot. {}%'.format(in_ratio[0], overall_ratio[0]))
        self.m_n_slider = forms.Slider()
        self.m_n_slider.MinValue = min_v
        self.m_n_slider.MaxValue = max_v
        self.m_n_slider.TickFrequency = 5
        self.m_n_slider.SnapToTick = True
        self.m_n_slider.Value = in_ratio[0]
        self.m_n_slider.ValueChanged += self.OnUpdateNorthLabel
        
        self.m_e_label = forms.Label(Text = 'East: rel. {}%   tot. {}%'.format(in_ratio[1], overall_ratio[1]))
        self.m_e_slider = forms.Slider()
        self.m_e_slider.MinValue = min_v
        self.m_e_slider.MaxValue = max_v
        self.m_e_slider.TickFrequency = 5
        self.m_e_slider.SnapToTick = True
        self.m_e_slider.Value = in_ratio[1]
        self.m_e_slider.ValueChanged += self.OnUpdateEastLabel
        
        self.m_s_label = forms.Label(Text = 'South: rel. {}%   tot. {}%'.format(in_ratio[2], overall_ratio[2]))
        self.m_s_slider = forms.Slider()
        self.m_s_slider.MinValue = min_v
        self.m_s_slider.MaxValue = max_v
        self.m_s_slider.TickFrequency = 5
        self.m_s_slider.SnapToTick = True
        self.m_s_slider.Value = in_ratio[2]
        self.m_s_slider.ValueChanged += self.OnUpdateSouthLabel
        
        self.m_w_label = forms.Label(Text = 'West: rel. {}%   tot. {}%'.format(in_ratio[3], overall_ratio[3]))
        self.m_w_slider = forms.Slider()
        self.m_w_slider.MinValue = min_v
        self.m_w_slider.MaxValue = max_v
        self.m_w_slider.TickFrequency = 5
        self.m_w_slider.SnapToTick = True
        self.m_w_slider.Value = in_ratio[3]
        self.m_w_slider.ValueChanged += self.OnUpdateWestLabel
        
        self.m_button = forms.Button(Text = 'Change it!')
        self.m_button.Click += self.OnButtonClick
        
        layout = forms.DynamicLayout()
        layout.Padding = drawing.Padding(10)
        layout.Spacing = drawing.Size(5, 5)
        
        layout.AddRow(self.m_n_slider, self.m_n_label)
        layout.AddRow(self.m_s_slider, self.m_s_label)
        layout.AddRow(self.m_e_slider, self.m_e_label)
        layout.AddRow(self.m_w_slider, self.m_w_label)
        layout.AddRow(None)
        layout.AddRow(None, self.m_button)
        self.Content = layout
    
    def OnUpdateNorthLabel(self, s, e):
        self.m_n_label.Text = 'North: rel. {}%'.format(s.Value)
    
    def OnUpdateEastLabel(self, s, e):
        self.m_e_label.Text = 'East: rel. {}%'.format(s.Value)
    
    def OnUpdateSouthLabel(self, s, e):
        self.m_s_label.Text = 'South: rel. {}%'.format(s.Value)
    
    def OnUpdateWestLabel(self, s, e):
        self.m_w_label.Text = 'West: rel. {}%'.format(s.Value)
    
    def OnButtonClick(self, s, e):
        values = [self.m_n_slider.Value, self.m_e_slider.Value, 
        self.m_s_slider.Value, self.m_w_slider.Value]
        self.Close(values)

# GO BACK TO POLLINATION RHINO
#---------------------------------------------------------------------------------------------#

# create objects first
hb_rooms = []
for rm in rooms:
    hb_dict = json.loads(rm.ToHBObject().ToJson() )
    hb_obj = hb_dict_util.dict_to_object(hb_dict, False)
    if not hb_obj: raise ValueError(e)
    hb_rooms.append(hb_obj)

face_group = get_faces_group_by_orientation(hb_rooms)
in_ratio = get_current_wwr(face_group)
overall_ratio = get_current_wwr(face_group, True)

# run eto here
dialog = RatioSelection(in_ratio, overall_ratio)
rc = dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
out_ratio = map(lambda n: n / 100, rc)

breps = get_aperture_breps(face_group, in_ratio, out_ratio)

if not breps:
    raise ValueError('No apertures.')

for rm in rooms:
    # delete all apertures
    for apt in rm.Apertures:
        doc.Objects.Delete(apt, True)
    
    # create new apertures
    apertures = []
    for brp in breps:
        apt = sh.Objects.ApertureObject(brp)
        apt.Id = System.Guid.NewGuid()
        apertures.append(apt)
    
    # add new apertures
    new_room, added_apts = rm.AddApertures(apertures, tol, a_tol)
    if not added_apts: continue
    
    for apt in added_apts: 
        doc.Objects.AddRhinoObject(apt)
    
    # create a List of rooms
    new_room.Id = rm.Id
    rooms = List[sh.Objects.RoomObject]()
    rooms.Add(new_room)
    
    PollinationRhinoPlugIn.UpdateHBObjs(doc, rooms)
doc.Views.Redraw()
