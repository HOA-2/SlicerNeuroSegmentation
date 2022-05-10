import vtk, qt, ctk, slicer
import os
from slicer.util import VTKObservationMixin
import logging

class NeuroSegmentInputMarkupsWidget(qt.QWidget, VTKObservationMixin):
  def __init__(self):
    qt.QWidget.__init__(self)
    VTKObservationMixin.__init__(self)
    self.isUpdatingGUIFromMRML = False
    self.setup()

  def setup(self):
    """
    Setup the widget UI
    """
    contentsLayout = qt.QHBoxLayout()
    contentsLayout.setContentsMargins(0, 0, 0, 0)
    contentsLayout.setSpacing(0)
    self.setLayout(contentsLayout)
    self.setContentsMargins(0, 0, 0, 0)

    moduleName = "NeuroSegmentParcellation"
    scriptedModulesPath = os.path.dirname(slicer.util.modulePath(moduleName))
    uiPath = os.path.join(scriptedModulesPath, 'Resources', 'UI', 'NeuroSegmentInputMarkupsWidget.ui')
    self.uiWidget = slicer.util.loadUI(uiPath)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    self.ui.markupsPlaceWidget.setMRMLScene(slicer.mrmlScene)
    self.ui.markupsPlaceWidget.findChild("QToolButton", "MoreButton").setVisible(False)
    self.ui.markupsPlaceWidget.findChild("ctkColorPickerButton", "ColorButton").setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Expanding)

    self.updateGUIFromMRML()
    self.layout().addWidget(self.uiWidget)

    self.connect('destroyed(QObject*)', self.onDestroyed)

    self.ui.visibilityButton.connect('clicked(bool)', self.onVisibilityClicked)
    self.ui.lockButton.connect('clicked(bool)', self.onLockClicked)

  def onDestroyed(self):
    self.removeObservers()

  def setInputMarkupsNode(self, inputMarkupsNode):
    if inputMarkupsNode == self.getInputMarkupsNode():
      return
    self.ui.markupsPlaceWidget.setCurrentNode(inputMarkupsNode)

    self.removeObservers(self.onMarkupsNodeModified)
    self.removeObservers(self.onDisplayNodeModified)
    if inputMarkupsNode:
      self.addObserver(inputMarkupsNode, vtk.vtkCommand.ModifiedEvent, self.onMarkupsNodeModified)
      self.addObserver(inputMarkupsNode, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.onDisplayNodeModified)
    self.updateGUIFromMRML()

  def onMarkupsNodeModified(self, markupsNode=None, event=None):
    self.updateGUIFromMRML()

  def onDisplayNodeModified(self, displayNode=None, event=None):
    """
    Method when the ModifiedEvent is invoked on the output model display node.
    """
    self.updateGUIFromMRML()

  def onVisibilityClicked(self):
    """
    Method called when the visibility button is clicked.
    """
    logging.info("Visibility button clicked")
    if self.isUpdatingGUIFromMRML:
      return
    modelNode = self.getInputMarkupsNode()
    if modelNode is None:
      logging.error("onVisibilityClicked: Invalid model node")
      return
    modelNode.SetDisplayVisibility(not modelNode.GetDisplayVisibility())
    logging.info("Visibility updated")

  def onLockClicked(self):
    """
    Method called when the lock button is clicked
    """
    logging.info("Lock button clicked")
    inputMarkupsNode = self.getInputMarkupsNode()
    if inputMarkupsNode is None:
      logging.error("onLockClicked: Invalid markups node")
      return
    inputMarkupsNode.SetLocked(not inputMarkupsNode.GetLocked())
    logging.info("Lock state updated")

  def getInputMarkupsNode(self):
    """
    Returns the current input markups node
    """
    return self.ui.markupsPlaceWidget.currentNode()
    
  def getInputMarkupsDisplayNode(self):
    """
    Returns the current input markups display node
    """
    inputMarkupsNode = self.getInputMarkupsNode()
    if inputMarkupsNode is None:
      return None
    inputMarkupsNode.CreateDefaultDisplayNodes()
    return inputMarkupsNode.GetDisplayNode()

  def updateGUIFromMRML(self):
    """
    Update the GUI from the markups node.
    """
    if self.isUpdatingGUIFromMRML:
      return
    self.isUpdatingGUIFromMRML = True

    inputMarkupsNode = self.getInputMarkupsNode()
    self.uiWidget.enabled = not inputMarkupsNode is None

    visible = False
    if inputMarkupsNode:
      visible = inputMarkupsNode.GetDisplayVisibility()
    if visible:
      self.ui.visibilityButton.setIcon(qt.QIcon(":/Icons/Small/SlicerVisible.png"))
    else:
      self.ui.visibilityButton.setIcon(qt.QIcon(":/Icons/Small/SlicerInvisible.png"))

    locked = False
    if inputMarkupsNode:
      locked = inputMarkupsNode.GetLocked()
    if locked:
      self.ui.lockButton.setIcon(qt.QIcon(":/Icons/Small/SlicerLock.png"))
    else:
      self.ui.lockButton.setIcon(qt.QIcon(":/Icons/Small/SlicerUnlock.png"))

    self.isUpdatingGUIFromMRML = False
