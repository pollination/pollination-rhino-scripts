"""
Create rooms from closed curves.
"""

# import rhinocommon and Eto
import Rhino
import System
import Rhino.UI
import Eto.Drawing as drawing
import Eto.Forms as forms

# import pollination part
import clr
clr.AddReference('Share.dll')
clr.AddReference('HoneybeeSchema.dll')
clr.AddReference('Honeybee.UI.Rhino.dll')
import HoneybeeSchema as HB # csharp version of HB Schema
import Share as SH # It contains Pollination RhinoObject classes
import Share.Convert as CO # It contains utilities to convert RhinoObject <> HB Schema
import Honeybee.UI as HU

# SELECTION PART
#---------------------------------------------------------------------------------------------#
# doc info
doc = Rhino.RhinoDoc.ActiveDoc
tol = doc.ModelAbsoluteTolerance
a_tol = doc.ModelAngleToleranceRadians
current_model = SH.Entity.ModelEntityTable.Instance.CurrentModelEntity
doc_unit = Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem

default_height = {
    Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem.Meters: 3,
    Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem.Centimeters: 300,
    Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem.Millimeters: 3000,
    Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem.Feet: 9.84,
    Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem.Inches: 118
}

if not default_height.has_key(doc_unit):
    raise ValueError('Unit not supported.')

# define Eto grid
class RoomGridView(forms.Dialog[list]):
    
    def __init__(self, data):
        unit = str(doc_unit).lower()
        
        self._data_dict = {}
        self._data = data
        self.Title = "Closed curve - Room generator"
        self.Resizable = True
        self.m_gridview = forms.GridView()
        self.m_gridview.ShowHeader = True
        self.m_gridview.DataStore = data
        self.m_gridview.Height = 300
        self.m_gridview.Width = 300 
        self.m_gridview.CellDoubleClick += self.OnDoubleClickLayer
        
        self._header = ('LayerName', 'Height ({})'.format(unit), 'Export')
        
        column1 = forms.GridColumn()
        column1.HeaderText = self._header[0]
        column1.DataCell = forms.TextBoxCell(0)
        column1.Width = 195
        self.m_gridview.Columns.Add(column1)

        column2 = forms.GridColumn()
        column2.HeaderText = self._header[1]
        column2.Editable = True
        column2.DataCell = forms.TextBoxCell(1)
        column2.Width = 95
        self.m_gridview.Columns.Add(column2)
        
        self.m_button = forms.Button(self.OnClickButton)
        self.m_button.Text = 'Run It!'
        
        layout = forms.DynamicLayout()
        layout.Padding = drawing.Padding(10)
        layout.Spacing = drawing.Size(5, 5)
        layout.Add(forms.Label(Text = '1. Double click on a row to set room properties.'))
        layout.Add(forms.Label(Text = '2. One click on the height cell tso edit the room height.'))
        layout.Add(self.m_gridview)
        layout.Add(self.m_button)
        layout.Add(forms.Label(Text = 'Only planar closed curves are supported.'))
        self.Content = layout
    
    def OnClickButton(self, s, e):
        out_data = []
        
        for i, data in enumerate(self._data):
            name, height, cecked, geometries = data
            if geometries and self._data_dict.has_key(i):
                out_data.append([name, height, cecked, geometries, self._data_dict[i]])
        
        self.Close(out_data)
    
    def OnDoubleClickLayer(self, s, e):
        # Properties of the Model
        properties = current_model.HBModelProperties
        energy_prop = properties.Energy
        room_energy_prop = HB.RoomEnergyPropertiesAbridged()
        
        dialog = HU.Dialog_RoomEnergyProperty(energy_prop, room_energy_prop, True)
        dialog_rc = dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
        
        if dialog_rc:
            self._data_dict[e.Row] = dialog_rc

def select_objects(layer_table_names):
    objects = []
    for layer in layer_table_names:
        sub_objects = []
        for obj in Rhino.RhinoDoc.ActiveDoc.Objects:
            if layer_table_names[obj.Attributes.LayerIndex] == layer:
                # planar closed curve only
                geometry = obj.Geometry
                if isinstance(geometry, Rhino.Geometry.Curve) \
                and geometry.IsClosed and geometry.IsPlanar:
                    sub_objects.append(geometry)
        objects.append(sub_objects)
    return objects

def create_solid(crv, height):
    srf = Rhino.Geometry.Extrusion.CreateExtrusion(crv, Rhino.Geometry.Vector3d(0, 0, float(height))).ToBrep()
    brep = srf.CapPlanarHoles(tol)
    return brep

# Get dataset
layer_table = [_ for _ in Rhino.RhinoDoc.ActiveDoc.Layers if (not _.IsLocked and _.IsValid)]
layer_table_names = map(str, layer_table)
heights = [default_height[doc_unit]] * len(layer_table_names)
checked = [False] * len(layer_table_names)

# prepare geometries
geometries = select_objects(layer_table_names)

data = [[n, h, c, g] for n, h, c, g in zip(layer_table_names, heights, checked, geometries)]

# run eto
dialog = RoomGridView(data)
rc = dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)

# TODO: fix refresh issue with ModelDialog
if rc:
    # create pollination rooms
    for dt in rc:
        print dt
        name, height, checked, geometries, properties = dt
        #if not checked: continue
        for geo in geometries:
            geo = create_solid(geo, height)
            if (geo is None or not geo.IsValid or not geo.IsSolid): continue
            test = doc.Objects.AddBrep(geo)
            brep_object = doc.Objects.Find(test)
            
            if brep_object:
                brep = Rhino.Geometry.Brep.TryConvertBrep(brep_object.Geometry)
                new_room = SH.Objects.RoomObject(brep, tol)
                new_room.SetEnergyProp(properties)
                
                success = doc.Objects.Replace(Rhino.DocObjects.ObjRef(brep_object.Id), new_room)
                
                # remove if it exists
                for room in current_model.Rooms:
                    if room.ObjectId == brep_object.Id:
                        current_model.Rooms.Remove(room)
                
                current_model.Rooms.Add(Rhino.DocObjects.ObjRef(brep_object.Id))

doc.Views.Redraw()