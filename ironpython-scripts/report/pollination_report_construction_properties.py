"""
Create a simple report on runtime to check energy properties of room constructions
------------------------------------------------------------------------------
Instructions:
    1. Run the script
------------------------------------------------------------------------------
Strategy:
    1. Get all Pollination constructions
    2. Use Honeybee for reporting
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
import HoneybeeSchema as HB # csharp version of HB Schema
import Share as SH # It contains Pollination RhinoObject classes
import Share.Convert as CO # It contains utilities to convert RhinoObject <> HB Schema

# import List collection
from System.Collections.Generic import List

try:  # import honeybee dependencies
    import json
    import honeybee.dictutil as hb_dict_util
    from honeybee_energy.construction.opaque import OpaqueConstruction
    from honeybee_energy.construction.window import WindowConstruction
    from honeybee_energy.construction.windowshade import WindowConstructionShade
    from honeybee_energy.construction.air import AirBoundaryConstruction
    from honeybee_energy.construction.shade import ShadeConstruction
    from ladybug.datatype.rvalue import RValue
    from ladybug.datatype.uvalue import UValue
except ImportError as e:
    raise ImportError('\nFailed to import:\n\t{}'.format(e))

# MODEL COMMON INFO
#---------------------------------------------------------------------------------------------#
# doc info
doc = Rhino.RhinoDoc.ActiveDoc
tol = doc.ModelAbsoluteTolerance
a_tol = doc.ModelAngleToleranceRadians
current_model = SH.Entity.ModelEntityTable.Instance.CurrentModelEntity
doc_unit = Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem

# REPORTING PART
#---------------------------------------------------------------------------------------------#

# define Eto grid
class ConstructionGridView(forms.Dialog[bool]):
    
    def __init__(self, data):
        unit = str(doc_unit).lower()
        
        self.Title = "Constructions report"
        self.Resizable = True
        self.m_gridview = forms.GridView()
        self.m_gridview.ShowHeader = True
        self.m_gridview.Height = 300
        
        self.m_gridview.DataStore = data
        
        column1 = forms.GridColumn()
        column1.HeaderText = 'ConstrName'
        column1.Editable = True
        column1.DataCell = forms.TextBoxCell(0)
        self.m_gridview.Columns.Add(column1)

        column2 = forms.GridColumn()
        column2.HeaderText = 'R_val [m2-K/W]'
        column2.Editable = True
        column2.DataCell = forms.TextBoxCell(1)
        self.m_gridview.Columns.Add(column2)

        column3 = forms.GridColumn()
        column3.HeaderText = 'R_val [h-ft2-F/Btu]'
        column3.Editable = True
        column3.DataCell = forms.TextBoxCell(2)
        self.m_gridview.Columns.Add(column3)

        column4 = forms.GridColumn()
        column4.HeaderText = 'U_factor [W/m2-K]'
        column4.Editable = True
        column4.DataCell = forms.TextBoxCell(3)
        self.m_gridview.Columns.Add(column4)
        
        column5 = forms.GridColumn()
        column5.HeaderText = 'U_factor [Btu/h-ft2-F]'
        column5.Editable = True
        column5.DataCell = forms.TextBoxCell(4)
        self.m_gridview.Columns.Add(column5)
        
        column6 = forms.GridColumn()
        column6.HeaderText = 'T_sol [0-1]'
        column6.Editable = True
        column6.DataCell = forms.TextBoxCell(5)
        self.m_gridview.Columns.Add(column6)
        
        column7 = forms.GridColumn()
        column7.HeaderText = 'VLT [0-1]'
        column7.Editable = True
        column7.DataCell = forms.TextBoxCell(6)
        self.m_gridview.Columns.Add(column7)
        
        column8 = forms.GridColumn()
        column8.HeaderText = 'MassAreaDensity [kg m-2]'
        column8.Editable = True
        column8.DataCell = forms.TextBoxCell(7)
        self.m_gridview.Columns.Add(column8)
        
        column9 = forms.GridColumn()
        column9.HeaderText = 'Thickness [m]'
        column9.Editable = True
        column9.DataCell = forms.TextBoxCell(8)
        self.m_gridview.Columns.Add(column9)
        
        layout = forms.DynamicLayout()
        layout.Padding = drawing.Padding(10)
        layout.Spacing = drawing.Size(5, 5)
        layout.Add(self.m_gridview)
        
        self.Content = layout

# HONEYBEE PART
#---------------------------------------------------------------------------------------------#

# get all active constructions
model = json.loads(current_model.GetHBModel().ToJson())
hb_model = hb_dict_util.dict_to_object(model, False)
constuctions = hb_model.properties.energy.constructions

# check if it is empty
if not constuctions:
    forms.MessageBox.Show("Please, assign constructions first!")

data = []
for constr in constuctions:
    # get the materials, r-value and u-factor
    if isinstance(constr, AirBoundaryConstruction) \
    or isinstance(constr, ShadeConstruction): continue
    layers = constr.layers
    r_val_si = constr.r_value
    r_val_ip = RValue().to_ip([r_val_si], 'm2-K/W')[0][0]
    u_fac_si = constr.u_factor
    u_fac_ip = UValue().to_ip([u_fac_si], 'W/m2-K')[0][0]
    
    # get the transmittance
    if isinstance(constr, WindowConstruction):
        t_sol = constr.solar_transmittance
        t_vis = constr.visible_transmittance
        mass_area_density = 0
    elif isinstance(constr, WindowConstructionShade):  # get unshaded transmittance
        t_sol = constr.window_construction.solar_transmittance
        t_vis = constr.window_construction.visible_transmittance
        mass_area_density = 0
        
    else:
        t_sol = 0
        t_vis = 0
        mass_area_density = constr.mass_area_density
    
    thickness = constr.thickness
    
    numeric = [r_val_si, \
                r_val_ip, u_fac_si, u_fac_ip, \
                t_sol, t_vis, mass_area_density, thickness]
    
    numeric = list(map(lambda _ : round(_, 3), numeric))
    
    row = [constr.display_name]
    row.extend(numeric)
    data.append(row)

# show the table
if constuctions:
    dialog = ConstructionGridView(data)
    rc = dialog.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)