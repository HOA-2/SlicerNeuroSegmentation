
#-----------------------------------------------------------------------------
set(MODULE_NAME NeuroSegmentParcellation)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  NeuroSegmentParcellationLibs/NeuroSegmentParcellationVisitor.py
  NeuroSegmentParcellationLibs/NeuroSegmentParcellationLogic.py
  NeuroSegmentParcellationLibs/NeuroSegmentMarkupsIntersectionDisplayManager.py
  NeuroSegmentParcellationLibs/NeuroSegmentOutputToolWidget.py
  NeuroSegmentParcellationLibs/NeuroSegmentInputMarkupsWidget.py
  NeuroSegmentParcellationLibs/NeuroSegmentInputMarkupsFrame.py
  )

set(MODULE_PYTHON_ICON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  )

set(MODULE_PYTHON_UI_RESOURCES
  Resources/UI/${MODULE_NAME}.ui
  Resources/UI/NeuroSegmentInputMarkupsWidget.ui
  Resources/UI/NeuroSegmentOutputToolWidget.ui
  )

set(MODULE_PYTHON_PARCELLATION_RESOURCES
  Resources/Parcellation/parcellation.qry
  )

set(MODULE_PYTHON_RESOURCES
  ${MODULE_PYTHON_ICON_RESOURCES}
  ${MODULE_PYTHON_UI_RESOURCES}
  ${MODULE_PYTHON_PARCELLATION_RESOURCES}
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  slicer_add_python_unittest(SCRIPT ${MODULE_NAME}.py)

endif()
