
import ast
import vtk, slicer

#TODO
INPUT_MARKUPS_REFERENCE = "InputMarkups"
OUTPUT_MODEL_REFERENCE = "OutputModel"
TOOL_NODE_REFERENCE = "ToolNode"

class NeuroSegmentParcellationVisitor(ast.NodeVisitor):
  """TODO
  """

  def __init__(self):
    self.parameterNode = None

  def setParameterNode(self, parameterNode):
    self.parameterNode = parameterNode

  def visit_Assign(self, node):
    if len(node.targets) > 1:
        logging.error("Invalid assignment in line %d" % node.lineno)
        return

    if 'target' in node._fields:
      target = node.target
    if 'targets' in node._fields:
      target = node.targets[0]

    if not isinstance(target, ast.Name):
      logging.error("Invalid assignment in line %d" % node.lineno)
      return

    if target.id == "_Planes":
      self.process_InputNodes(node.value, "vtkMRMLMarkupsPlaneNode")
      return
    elif target.id == "_Curves":
      curveNodes = self.process_InputNodes(node.value, "vtkMRMLMarkupsCurveNode")
      for curveNode in curveNodes:
        curveNode.SetCurveTypeToShortestDistanceOnSurface()
      return
    elif target.id == "_ClosedCurves":
      curveNodes = self.process_InputNodes(node.value, "vtkMRMLMarkupsClosedCurveNode")
      for curveNode in curveNodes:
        curveNode.SetCurveTypeToShortestDistanceOnSurface()
      return
    elif target.id == "_DistanceWeightingFunction":
      self.distanceWeightingFunction = node.value.s
      return

    nodes = self.visit(node.value)

    outputModel = slicer.util.getFirstNodeByClassByName("vtkMRMLModelNode", target.id)
    if outputModel is None:
      outputModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", target.id)
    outputModelDisplayNode = outputModel.GetDisplayNode()
    if outputModelDisplayNode is None:
      outputModel.CreateDefaultDisplayNodes()
      outputModelDisplayNode = outputModel.GetDisplayNode()
      outputModelDisplayNode.SetVisibility(False)
    self.parameterNode.AddNodeReferenceID(OUTPUT_MODEL_REFERENCE, outputModel.GetID())

    inputSeed = slicer.util.getFirstNodeByClassByName("vtkMRMLMarkupsFiducialNode", target.id + "_SeedPoints")
    if inputSeed is None:
      inputSeed = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", target.id + "_SeedPoints")
      inputSeed.CreateDefaultDisplayNodes()

    toolNode = slicer.util.getFirstNodeByClassByName("vtkMRMLModelNode", outputModel.GetName() + "_BoundaryCut")
    if toolNode is None:
      toolNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLDynamicModelerNode", outputModel.GetName() + "_BoundaryCut")
    toolNode.SetToolName(slicer.vtkSlicerDynamicModelerBoundaryCutTool().GetName())
    toolNode.SetNodeReferenceID("BoundaryCut.OutputModel", outputModel.GetID())
    toolNode.SetNodeReferenceID("BoundaryCut.InputSeed", inputSeed.GetID())
    for inputNode in nodes:
      toolNode.AddNodeReferenceID("BoundaryCut.InputBorder", inputNode.GetID())
    toolNode.ContinuousUpdateOff()
    self.parameterNode.AddNodeReferenceID(TOOL_NODE_REFERENCE, toolNode.GetID())

  def process_InputNodes(self, node, className):
    if not isinstance(node, ast.List):
      logging.error("Expected list of planes in line %d" % node.lineno)
      return
    planeNames = [e.id for e in node.elts]
    inputNodes = []
    for name in planeNames:
      inputNode = slicer.util.getFirstNodeByClassByName(className, name)
      if not inputNode:
        inputNode = slicer.mrmlScene.AddNewNodeByClass(className, name)
        inputNode.CreateDefaultDisplayNodes()
        displayNode = inputNode.GetDisplayNode()
        if displayNode:
          displayNode.SetGlyphScale(4.0)
          if className == "vtkMRMLMarkupsPlaneNode":
            displayNode.HandlesInteractiveOn()
      if inputNode.IsA("vtkMRMLMarkupsCurveNode"):
        inputNode.SetAttribute("DistanceWeightingFunction", self.distanceWeightingFunction)
        inputNodes.append(inputNode)
      self.parameterNode.AddNodeReferenceID(INPUT_MARKUPS_REFERENCE, inputNode.GetID())
    return inputNodes

  def visit_Name(self, node):
    slicerNode = slicer.util.getNode(node.id)
    return [slicerNode]

  def visit_Call(self, node):
    pass

  def visit_BinOp(self, node):
    leftValue = node.left
    rightValue = node.right
    if leftValue == None or rightValue == None:
      logging.error("Invalid binary operator arguments!")
      return

    leftNodes = self.visit(leftValue)
    rightNodes = self.visit(rightValue)
    return leftNodes + rightNodes

  def visit_UnaryOp(self, node):
    logging.error("Unary operator not supported!")