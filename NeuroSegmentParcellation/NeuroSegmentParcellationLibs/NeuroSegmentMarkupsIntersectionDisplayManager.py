import vtk, qt, ctk, slicer
import logging
from slicer.util import VTKObservationMixin
import numpy as np


class NeuroSegmentMarkupsIntersectionPipeline(VTKObservationMixin):
  def __init__(self, curveNode, sliceNode):
    VTKObservationMixin.__init__(self)

    self.glyphScale = 0.5

    self.intersectionPoints_XY = vtk.vtkPolyData()

    self.glyphSource = slicer.vtkMarkupsGlyphSource2D()
    self.glyphSource.SetGlyphType(slicer.vtkMarkupsGlyphSource2D.GlyphCrossDot)

    self.glypher = vtk.vtkGlyph2D()
    self.glypher.SetInputData(self.intersectionPoints_XY)
    self.glypher.SetScaleFactor(1.0)
    self.glypher.SetSourceConnection(self.glyphSource.GetOutputPort())

    self.mapper = vtk.vtkPolyDataMapper2D()
    self.mapper.SetInputConnection(self.glypher.GetOutputPort())
    self.mapper.ScalarVisibilityOff()
    mapperCoordinate = vtk.vtkCoordinate()
    mapperCoordinate.SetCoordinateSystemToDisplay()
    self.mapper.SetTransformCoordinate(mapperCoordinate)

    self.property = vtk.vtkProperty2D()
    self.property.SetColor(0.4, 1.0, 1.0)
    self.property.SetPointSize(3.)
    self.property.SetLineWidth(3.)
    self.property.SetOpacity(1.)

    self.actor = vtk.vtkActor2D()
    self.actor.SetMapper(self.mapper)
    self.actor.SetProperty(self.property)

    self.curveNode = curveNode
    self.sliceNode = sliceNode

    self.visibility = True

  def setVisibility(self, visibility):
    self.visibility = visibility
    self.updateActorFromMRML()
    sliceView = self.getSliceView()
    if sliceView:
      sliceView.scheduleRender()

  def setGlyphType(self, glyphType):
    self.glyphSource.SetGlyphType(glyphType)
    sliceView = self.getSliceView()
    if sliceView:
      sliceView.scheduleRender()

  def setGlyphScale(self, glyphScale):
    self.glyphScale = glyphScale
    sliceView = self.getSliceView()
    self.updateActorFromMRML()
    if sliceView:
      sliceView.scheduleRender()

  def addActor(self):
    if self.sliceNode is None or self.curveNode is None:
      return

    renderer = self.getRenderer()
    if renderer is None:
      return

    renderer.AddActor2D(self.actor)

    self.addObserver(self.sliceNode, vtk.vtkCommand.ModifiedEvent, self.updateActorFromMRML)
    self.addObserver(self.curveNode, vtk.vtkCommand.ModifiedEvent, self.updateActorFromMRML)
    self.addObserver(self.curveNode, slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.updateActorFromMRML)
    self.addObserver(self.curveNode, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent , self.updateActorFromMRML)
    self.updateActorFromMRML()

    sliceView = self.getSliceView()
    if sliceView:
      sliceView.scheduleRender()

  def removeActor(self):
    renderer = self.getRenderer()
    if renderer is None:
      return

    renderer.RemoveActor2D(self.actor)
    self.removeObservers(self.updateActorFromMRML)

  def updateActorFromMRML(self, caller=None, event=None):
    if not self.visibility:
      self.actor.SetVisibility(False)
      return

    if self.sliceNode is None or self.curveNode is None:
      self.actor.SetVisibility(False)
      return

    if self.curveNode.GetNumberOfControlPoints() <= 0 or not self.curveNode.GetDisplayVisibility():
      self.actor.SetVisibility(False)
      return

    displayNode = self.curveNode.GetDisplayNode()
    if displayNode:
      viewNodeIDs = displayNode.GetViewNodeIDs()
      if not self.sliceNode.GetID() in viewNodeIDs:
        self.actor.SetVisibility(False)
        return

    self.actor.SetVisibility(True)

    xyToRASMatrix = self.sliceNode.GetXYToRAS()

    sliceNormal_RAS = np.array([0.0, 0.0, 1.0, 0.0])
    xyToRASMatrix.MultiplyPoint(sliceNormal_RAS, sliceNormal_RAS)

    sliceOrigin_RAS = np.array([0.0, 0.0, 0.0, 1.0])
    xyToRASMatrix.MultiplyPoint(sliceOrigin_RAS, sliceOrigin_RAS)

    slicePlane_RAS = vtk.vtkPlane()
    slicePlane_RAS.SetNormal(sliceNormal_RAS[:3])
    slicePlane_RAS.SetOrigin(sliceOrigin_RAS[:3])

    intersectionPoints_RAS = vtk.vtkPoints()
    self.curveNode.GetPointsOnPlaneWorld(slicePlane_RAS, intersectionPoints_RAS)

    rasToXYMatrix = vtk.vtkMatrix4x4()
    vtk.vtkMatrix4x4.Invert(xyToRASMatrix, rasToXYMatrix)

    rasToXYTransform = vtk.vtkTransform()
    rasToXYTransform.SetMatrix(rasToXYMatrix)

    intersectionPolyData_RAS = vtk.vtkPolyData()
    intersectionPolyData_RAS.SetPoints(intersectionPoints_RAS)

    transformFilter = vtk.vtkTransformPolyDataFilter()
    transformFilter.SetTransform(rasToXYTransform)
    transformFilter.SetInputData(intersectionPolyData_RAS)
    transformFilter.Update()
    self.intersectionPoints_XY.DeepCopy(transformFilter.GetOutput())

    renderWindow = self.getRenderWindow()
    screenSize = renderWindow.GetScreenSize()
    screenSizePixel = np.sqrt(screenSize[0] * screenSize[0] + screenSize[1] * screenSize[1])
    screenScaleFactor = 0.02 * self.glyphScale
    controlPopintSize = screenSizePixel * screenScaleFactor
    self.glypher.SetScaleFactor(controlPopintSize)

    displayNode = self.curveNode.GetDisplayNode()
    if displayNode:
      color = displayNode.GetSelectedColor()
      self.property.SetColor(color)

  def getSliceView(self):
    if self.sliceNode is None:
      return None
    viewTag = self.sliceNode.GetSingletonTag()
    layoutManager = slicer.app.layoutManager()
    sliceWidget = layoutManager.sliceWidget(viewTag)
    return sliceWidget.sliceView()

  def getRenderWindow(self):
    sliceView = self.getSliceView()
    if sliceView is None:
      return None
    renderWindow = sliceView.renderWindow()
    return renderWindow

  def getRenderer(self):
    renderWindow = self.getRenderWindow()
    if renderWindow is None:
      return None
    return renderWindow.GetRenderers().GetItemAsObject(0)

class NeuroSegmentMarkupsIntersectionDisplayManager(VTKObservationMixin):

  def __init__(self):
    VTKObservationMixin.__init__(self)

    self.viewPipelines = {} # Key is view name, value is dict containing pipelines
                            # Key of nested dict is markups node, value is pipeline object
    self.visibility = True
    self.glyphScale = 0.5

    self.addObserver(slicer.mrmlScene, slicer.vtkMRMLScene.NodeAddedEvent, self.onNodeAdded)
    self.addObserver(slicer.mrmlScene, slicer.vtkMRMLScene.NodeRemovedEvent, self.onNodeRemoved)

    layoutManager = slicer.app.layoutManager()
    layoutManager.connect('layoutChanged(int)', self.updatePipelines)

    self.updatePipelines()

  def setVisibility(self, visibility):
    self.visibility = visibility
    for sliceViewName, currentViewPipelines in self.viewPipelines.items():
      for curveNode, pipeline in currentViewPipelines.items():
        pipeline.setVisibility(visibility)

  def setGlyphType(self, glyphType):
    self.glyphType = glyphType
    for sliceViewName, currentViewPipelines in self.viewPipelines.items():
      for curveNode, pipeline in currentViewPipelines.items():
        pipeline.setGlyphType(glyphType)

  def setGlyphScale(self, glyphScale):
    self.glyphScale = glyphScale
    for sliceViewName, currentViewPipelines in self.viewPipelines.items():
      for curveNode, pipeline in currentViewPipelines.items():
        pipeline.setGlyphScale(glyphScale)

  def updatePipelines(self):
    self.removeAllActors()

    layoutManager = slicer.app.layoutManager()
    for sliceViewName in layoutManager.sliceViewNames():
      self.viewPipelines[sliceViewName] = {}

    curveNodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLMarkupsCurveNode")
    curveNodes.UnRegister(None)
    for curveIndex in range(curveNodes.GetNumberOfItems()):
      curveNode = curveNodes.GetItemAsObject(curveIndex)
      self.addViewActors(curveNode)

  def removeAllActors(self):
    for sliceViewName, currentViewPipelines in self.viewPipelines.items():
      for curveNode, pipeline in currentViewPipelines.items():
        pipeline.removeActor()
    self.viewPipelines = {}

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeAdded(self, scene, event, node):
    if not node or not node.IsA("vtkMRMLMarkupsCurveNode"):
      return
    self.addViewActors(node)

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeRemoved(self, scene, event, node):
    if not node or not node.IsA("vtkMRMLMarkupsCurveNode"):
      return
    self.removeCurveActors(node)

  def addViewActors(self, curveNode):
    if curveNode.GetAttribute("NeuroSegmentParcellation.NodeType") != "Orig":
      return

    layoutManager = slicer.app.layoutManager()

    for sliceViewName, currentViewPipelines in self.viewPipelines.items():
      if curveNode in currentViewPipelines.keys():
        continue

      widget = layoutManager.sliceWidget(sliceViewName)
      sliceLogic = widget.sliceLogic()
      sliceNode = sliceLogic.GetSliceNode()

      pipeline = NeuroSegmentMarkupsIntersectionPipeline(curveNode, sliceNode)
      currentViewPipelines[curveNode] = pipeline
      pipeline.setGlyphType(self.glyphType)
      pipeline.setGlyphScale(self.glyphScale)
      pipeline.addActor()

  def removeCurveActors(self, curveNode):
    for currentViewPipelines in self.viewPipelines.values():
      if not curveNode in currentViewPipelines.keys():
        continue

      pipeline = currentViewPipelines.pop(curveNode)
      pipeline.removeActor()
