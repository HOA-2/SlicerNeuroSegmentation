from pydoc import classname
import vtk, qt, ctk, slicer
import os
from slicer.util import VTKObservationMixin
import logging
from .NeuroSegmentInputMarkupsWidget import NeuroSegmentInputMarkupsWidget

class NeuroSegmentInputMarkupsFrame(qt.QWidget, VTKObservationMixin):
  def __init__(self, logic, className):
    qt.QWidget.__init__(self)
    VTKObservationMixin.__init__(self)
    self.logic = logic
    self.className = className
    self.isUpdatingGUIFromMRML = False
    self.setup()
    self.parameterNode = None

    self.markupsContainerWidget = None
    self.inputMarkupsWidgets = []

  def setup(self):
    """
    Setup the widget UI
    """
    contentsLayout = qt.QVBoxLayout()
    contentsLayout.setContentsMargins(0, 0, 0, 0)
    contentsLayout.setSpacing(0)
    self.setLayout(contentsLayout)
    self.setContentsMargins(0, 0, 0, 0)

    self.connect('destroyed(QObject*)', self.onDestroyed)

  def onDestroyed(self):
    self.removeObservers()

  def setParameterNode(self, parameterNode):
    if parameterNode == self.parameterNode:
      return
    self.parameterNode = parameterNode

    self.removeObservers(self.onParameterNodeModified)
    if parameterNode:
      self.addObserver(parameterNode, vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified)
    self.updateGUIFromMRML()

  def onParameterNodeModified(self, parameterNode=None, event=None):
    self.updateGUIFromMRML()

  def getMarkupsNodesFromWidgets(self):
    markupsNodes = []
    for widget in self.inputMarkupsWidgets:
      markupsNodes.append(widget.getInputMarkupsNode())
    return markupsNodes

  def getMarkupsNodesFromParameterNode(self):
    tempInputMarkups = self.logic.getInputMarkupNodes(self.parameterNode)
    inputMarkups = []
    for markupsNode in tempInputMarkups:
      if not markupsNode or not markupsNode.IsA(self.className):
        continue
      inputMarkups.append(markupsNode)
    return inputMarkups

  def createMarkupsContainerWidget(self, markupsNodes):
    inputMarkupsWidgets = []
    markupsLayout = qt.QFormLayout()
    for inputNode in markupsNodes:
      markupWidget = NeuroSegmentInputMarkupsWidget()
      markupWidget.setInputMarkupsNode(inputNode)
      markupsLayout.addRow(qt.QLabel(inputNode.GetName() + ":"), markupWidget)
      inputMarkupsWidgets.append(markupWidget)
    markupsWidget = qt.QWidget()
    markupsWidget.setLayout(markupsLayout)
    return markupsWidget, inputMarkupsWidgets

  def updateGUIFromMRML(self):
    """
    Update the GUI from the markups node.
    """
    if self.isUpdatingGUIFromMRML:
      return

    widgetMarkupsNodes = self.getMarkupsNodesFromWidgets()
    parameterMarkupsNodes = self.getMarkupsNodesFromParameterNode()
    if widgetMarkupsNodes == parameterMarkupsNodes:
      return

    self.isUpdatingGUIFromMRML = True

    if self.markupsContainerWidget:
      self.markupsContainerWidget.deleteLater()
      self.markupsContainerWidget = None

    self.enabled = not (self.parameterNode is None)
    self.inputMarkupsWidgets = []
    self.markupsContainerWidget, self.inputMarkupsWidgets = self.createMarkupsContainerWidget(parameterMarkupsNodes)

    self.layout().addWidget(self.markupsContainerWidget)

    self.isUpdatingGUIFromMRML = False
