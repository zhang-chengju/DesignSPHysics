#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
''' DesignSPHysics Special Options Selection Dialog. '''

import FreeCADGui

from PySide import QtGui

from mod.translation_tools import __
from mod.dialog_tools import error_dialog, warning_dialog, ok_cancel_dialog
from mod.enums import ObjectType
from mod.constants import APP_NAME
from mod.freecad_tools import setup_damping_environment

from mod.widgets.ml_piston_1d_config_dialog import MLPiston1DConfigDialog
from mod.widgets.ml_piston_2d_config_dialog import MLPiston2DConfigDialog
from mod.widgets.relaxation_zone_regular_config_dialog import RelaxationZoneRegularConfigDialog
from mod.widgets.relaxation_zone_irregular_config_dialog import RelaxationZoneIrregularConfigDialog
from mod.widgets.relaxation_zone_file_config_dialog import RelaxationZoneFileConfigDialog
from mod.widgets.relaxation_zone_uniform_config_dialog import RelaxationZoneUniformConfigDialog
from mod.widgets.acceleration_input_dialog import AccelerationInputDialog
from mod.widgets.damping_config_dialog import DampingConfigDialog
from mod.widgets.inlet_config_dialog import InletConfigDialog
from mod.widgets.chrono_config_dialog import ChronoConfigDialog

from mod.dataobjects.case import Case
from mod.dataobjects.mk_based_properties import MKBasedProperties
from mod.dataobjects.ml_piston_1d import MLPiston1D
from mod.dataobjects.ml_piston_2d import MLPiston2D
from mod.dataobjects.relaxation_zone_regular import RelaxationZoneRegular
from mod.dataobjects.relaxation_zone_irregular import RelaxationZoneIrregular
from mod.dataobjects.relaxation_zone_file import RelaxationZoneFile
from mod.dataobjects.relaxation_zone_uniform import RelaxationZoneUniform
from mod.dataobjects.damping import Damping


class SpecialOptionsSelectorDialog(QtGui.QDialog):
    ''' A dialog with different buttons to access special DesignSPHysics options for a case. '''

    def __init__(self):
        super().__init__()

        self.setWindowTitle(__("Special"))
        self.setMinimumWidth(200)
        self.sp_window_layout = QtGui.QVBoxLayout()

        self.sp_damping_button = QtGui.QPushButton(__("New Damping Zone"))
        self.sp_inlet_button = QtGui.QPushButton(__("Inlet/Outlet"))
        self.sp_chrono_button = QtGui.QPushButton(__("Coupling CHRONO"))
        self.sp_multilayeredmb_button = QtGui.QPushButton(__("Multi-layered Piston"))
        self.sp_multilayeredmb_menu = QtGui.QMenu()
        self.sp_multilayeredmb_menu.addAction(__("1 Dimension"))
        self.sp_multilayeredmb_menu.addAction(__("2 Dimensions"))
        self.sp_multilayeredmb_button.setMenu(self.sp_multilayeredmb_menu)

        self.sp_relaxationzone_button = QtGui.QPushButton(__("Relaxation Zone"))
        self.sp_relaxationzone_menu = QtGui.QMenu()
        self.sp_relaxationzone_menu.addAction(__("Regular waves"))
        self.sp_relaxationzone_menu.addAction(__("Irregular waves"))
        self.sp_relaxationzone_menu.addAction(__("External Input"))
        self.sp_relaxationzone_menu.addAction(__("Uniform velocity"))
        self.sp_relaxationzone_button.setMenu(self.sp_relaxationzone_menu)

        self.sp_accinput_button = QtGui.QPushButton(__("Acceleration Inputs"))

        self.sp_damping_button.clicked.connect(self.on_damping_option)
        self.sp_inlet_button.clicked.connect(self.on_inlet_option)
        self.sp_chrono_button.clicked.connect(self.on_chrono_option)
        self.sp_multilayeredmb_menu.triggered.connect(self.on_multilayeredmb_menu)
        self.sp_relaxationzone_menu.triggered.connect(self.on_relaxationzone_menu)
        self.sp_accinput_button.clicked.connect(self.on_accinput_button)

        for x in [self.sp_damping_button,
                  self.sp_inlet_button,
                  self.sp_chrono_button,
                  self.sp_multilayeredmb_button,
                  self.sp_relaxationzone_button,
                  self.sp_accinput_button]:
            self.sp_window_layout.addWidget(x)

        self.setLayout(self.sp_window_layout)
        self.exec_()

    def on_damping_option(self):
        ''' Defines damping button behaviour'''
        damping_group_name = setup_damping_environment()
        Case.instance().add_damping_group(damping_group_name)
        DampingConfigDialog(damping_group_name)
        self.accept()

    def on_inlet_option(self):
        ''' Defines Inlet/Outlet behaviour '''
        InletConfigDialog()
        self.accept()

    def on_chrono_option(self):
        ''' Defines Coupling CHRONO behaviour'''
        ChronoConfigDialog()
        self.accept()

    def on_multilayeredmb_menu(self, action):
        ''' Defines MLPiston menu behaviour'''
        # Get currently selected object
        try:
            selection = FreeCADGui.Selection.getSelection()[0]
        except IndexError:
            error_dialog(__("You must select an object"))
            return

        # Check if object is in the simulation
        if Case.instance().is_object_in_simulation(selection.Name):
            error_dialog(__("The selected object must be added to the simulation"))
            return

        # Check if it is fluid and warn the user.
        if Case.instance().get_simulation_object(selection.Name).type == ObjectType.FLUID:
            error_dialog(__("You can't apply a piston movement to a fluid.\nPlease select a boundary and try again"))
            return

        # Get selection mk
        selection_mk: int = Case.instance().get_simulation_object(selection.Name).obj_mk
        mk_properties: MKBasedProperties = Case.instance().get_mk_base_properties(selection_mk)

        # Check that this mk has no other motions applied
        if mk_properties.has_movements():
            # MK has motions applied. Warn the user and delete them
            motion_delete_warning = ok_cancel_dialog(APP_NAME, __("This mk already has motions applied. Setting a Multi-layered piston will delete all of its movement. Are you sure?"))
            if motion_delete_warning == QtGui.QMessageBox.Cancel:
                return
            mk_properties.remove_all_movements()

        # 1D or 2D piston
        if __("1 Dimension") in action.text():
            if mk_properties.mlayerpiston and not isinstance(mk_properties.mlayerpiston, MLPiston1D):
                overwrite_warn = ok_cancel_dialog(APP_NAME, __("You're about to overwrite a previous coupling movement for this mk. Are you sure?"))
                if overwrite_warn == QtGui.QMessageBox.Cancel:
                    return

            config_dialog = MLPiston1DConfigDialog(selection_mk, mk_properties.mlayerpiston)
            if config_dialog.result() == QtGui.QDialog.Accepted:
                warning_dialog(__("All changes have been applied for mk = {}").format(selection_mk))
            mk_properties.mlayerpiston = config_dialog.mlpiston1d

        if __("2 Dimensions") in action.text():
            # Check that there's no other multilayered piston for this mk
            if mk_properties.mlayerpiston and not isinstance(mk_properties.mlayerpiston, MLPiston2D):
                overwrite_warn = ok_cancel_dialog(APP_NAME, __("You're about to overwrite a previous coupling movement for this mk. Are you sure?"))
                if overwrite_warn == QtGui.QMessageBox.Cancel:
                    return

            config_dialog = MLPiston2DConfigDialog(selection_mk, mk_properties.mlayerpiston)
            if config_dialog.result() == QtGui.QDialog.Accepted:
                warning_dialog(__("All changes have been applied for mk = {}").format(selection_mk))
            mk_properties.mlayerpiston = config_dialog.mlpiston2d

        self.accept()

    def on_relaxationzone_menu(self, action):
        ''' Defines Relaxation Zone menu behaviour.'''

        # Check which type of relaxationzone it is
        if action.text() == __("Regular waves"):
            if Case.instance().relaxation_zone is not None:
                if not isinstance(Case.instance().relaxation_zone, RelaxationZoneRegular):
                    overwrite_warn = ok_cancel_dialog(__("Relaxation Zone"), __("There's already another type of Relaxation Zone defined. Continuing will overwrite it. Are you sure?"))
                    if overwrite_warn == QtGui.QMessageBox.Cancel:
                        return
                    else:
                        Case.instance().relaxation_zone = RelaxationZoneRegular()

            config_dialog = RelaxationZoneRegularConfigDialog(Case.instance().relaxation_zone)

            # Set the relaxation zone. Can be an object or be None
            Case.instance().relaxation_zone = config_dialog.relaxationzone
        if action.text() == __("Irregular waves"):
            if Case.instance().relaxation_zone is not None:
                if not isinstance(Case.instance().relaxation_zone, RelaxationZoneIrregular):
                    overwrite_warn = ok_cancel_dialog(__("Relaxation Zone"), __("There's already another type of Relaxation Zone defined. Continuing will overwrite it. Are you sure?"))
                    if overwrite_warn == QtGui.QMessageBox.Cancel:
                        return
                    else:
                        Case.instance().relaxation_zone = RelaxationZoneIrregular()

            config_dialog = RelaxationZoneIrregularConfigDialog(Case.instance().relaxation_zone)

            # Set the relaxation zone. Can be an object or be None
            Case.instance().relaxation_zone = config_dialog.relaxationzone
        if action.text() == __("External Input"):
            if Case.instance().relaxation_zone is not None:
                if not isinstance(Case.instance().relaxation_zone, RelaxationZoneFile):
                    overwrite_warn = ok_cancel_dialog(__("Relaxation Zone"), __("There's already another type of Relaxation Zone defined. Continuing will overwrite it. Are you sure?"))
                    if overwrite_warn == QtGui.QMessageBox.Cancel:
                        return
                    else:
                        Case.instance().relaxation_zone = RelaxationZoneFile()

            config_dialog = RelaxationZoneFileConfigDialog(Case.instance().relaxation_zone)

            # Set the relaxation zone. Can be an object or be None
            Case.instance().relaxation_zone = config_dialog.relaxationzone

        if action.text() == __("Uniform velocity"):
            if Case.instance().relaxation_zone is not None:
                if not isinstance(Case.instance().relaxation_zone, RelaxationZoneUniform):
                    overwrite_warn = ok_cancel_dialog(__("Relaxation Zone"), __("There's already another type of Relaxation Zone defined. Continuing will overwrite it. Are you sure?"))
                    if overwrite_warn == QtGui.QMessageBox.Cancel:
                        return
                    else:
                        Case.instance().relaxation_zone = RelaxationZoneUniform()

            config_dialog = RelaxationZoneUniformConfigDialog(Case.instance().relaxation_zone)

            # Set the relaxation zone. Can be an object or be None
            Case.instance().relaxation_zone = config_dialog.relaxationzone

        self.accept()

    def on_accinput_button(self):
        ''' Acceleration input button behaviour.'''
        accinput_dialog = AccelerationInputDialog(Case.instance().acceleration_input)
        result = accinput_dialog.exec_()

        if result == QtGui.QDialog.Accepted:
            Case.instance().acceleration_input = accinput_dialog.get_result()
