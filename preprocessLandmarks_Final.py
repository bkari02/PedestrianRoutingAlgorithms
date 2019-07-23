import sys
import qgis
from qgis.core import (
     QgsApplication, 
     QgsProcessingFeedback, 
     QgsVectorLayer,
     QgsCoordinateReferenceSystem
)
from qgis.analysis import QgsNativeAlgorithms

import processing as processing
from processing.core.Processing import Processing
Processing.initialize()
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

import networkx as nx 
import os
from osgeo import ogr

QgsApplication.setPrefixPath('/usr', True)
qgs = QgsApplication([], False)
qgs.initQgis()

# Append the path where processing plugin can be found
sys.path.append('/usr/share/qgis/python/plugins')
print(sys.path)
dirname = os.path.dirname(__file__)

#Set lambda (buffer distance around landmark), default = 50.0
bufferLambda=50.0
#Set beta (1- weight of landmark), default = 0.5 (= 50%)
beta_weight = 0.5 
#Set path to dual graph representation of streetnetwork including (dual) edges 
path_dual_edges = os.path.join(dirname, 'street_network/Muenster_edgesDual.shp')
#Set path to landmark layer with landmark_status field
path_landmarks = os.path.join(dirname, 'ismailLandamrks/Building_casestudy_area_3.gpkg')

# Predefine lot of pathes TO-DO: !ADD LOOPS AND REDUCE REDUNDANCIES!
path_to_output_1 = os.path.join(dirname, 'preprocessResults/output_layer.shp')
path_to_output_2 = os.path.join(dirname, 'preprocessResults/buffer_layer.shp')
path_to_output_3 = os.path.join(dirname, 'preprocessResults/intersected_layer.shp')
path_to_output_4 = os.path.join(dirname, 'preprocessResults/manipulatedAngular_layer.shp')
path_to_output_51 = os.path.join(dirname, 'street_network/computedRoutes1/nodesDualPath.shp')
path_to_output_52 = os.path.join(dirname, 'street_network/computedRoutes2/nodesDualPath.shp')
path_to_output_53 = os.path.join(dirname, 'street_network/computedRoutes3/nodesDualPath.shp')
path_to_output_61 = os.path.join(dirname, 'street_network/computedRoutes1/joined1.shp')
path_to_output_62 = os.path.join(dirname, 'street_network/computedRoutes2/joined2.shp')
path_to_output_63 = os.path.join(dirname, 'street_network/computedRoutes3/joined3.shp')
path_to_output_71 = os.path.join(dirname, 'street_network/computedRoutes1/matchPath.shp')
path_to_output_72 = os.path.join(dirname, 'street_network/computedRoutes2/matchPath.shp')
path_to_output_73 = os.path.join(dirname, 'street_network/computedRoutes3/matchPath.shp')
path_to_output_81 = os.path.join(dirname, 'withLandmark/polyRoute1.shp')
path_to_output_82 = os.path.join(dirname, 'withLandmark/polyRoute2.shp')
path_to_output_83 = os.path.join(dirname, 'withLandmark/polyRoute3.shp')
path_dual_nodes = os.path.join(dirname, 'street_network/Muenster_nodesDual.shp')
path_computed_1 = os.path.join(dirname, 'street_network/computedRoutes1/nodes.shp')
path_computed_2 = os.path.join(dirname, 'street_network/computedRoutes2/nodes.shp')
path_computed_3 = os.path.join(dirname, 'street_network/computedRoutes3/nodes.shp')
path_to_primal_edges = os.path.join(dirname, 'street_network/Muenster_edges.shp')

# Create QGIS-Layers from dual graph and landmarks
dualEdges = QgsVectorLayer(path_dual_edges, "DualEdges", "ogr")
landmarks = QgsVectorLayer(path_landmarks, "Landmarks", "ogr")

# Extract all landmarks that have landmark_status = true, so are considered as landmarks
params = { 
    'INPUT' : landmarks,
    'EXPRESSION' : "landmark_status = 1", 
    'OUTPUT' : path_to_output_1
}
feedback = QgsProcessingFeedback()
res = processing.run('native:extractbyexpression', params, feedback=feedback)

# Create buffer around landmarks with distance bufferLambda 
paramsBuf= { 
    'INPUT' : res['OUTPUT'],
    'DISTANCE' : bufferLambda, 
    'OUTPUT' : path_to_output_2
} 
res2 = processing.run('native:buffer', paramsBuf, feedback=feedback)

# add landmark status to edges that intersect with landmark buffer
paramsIntersect= { 
    'INPUT' : dualEdges,
    'JOIN' : res2['OUTPUT'],
    'PREDICATE' : 0,
    'JOIN_FIELDS' : 'landmark_s',
    'METHOD' : 0,  
    'OUTPUT' : path_to_output_3
} 
res3 = processing.run('qgis:joinattributesbylocation', paramsIntersect, feedback=feedback)

# manipulate angular change value with formaular (angular_change_in_degree * beta_weight = manipulated_value)
paramsRefactor= { 
    'INPUT' : res3['OUTPUT'],
    'FIELDS_MAPPING' : [{'name': 'u',
                        'type': 10,
                        'length': 80,
                        'precision': 0,
                        'expression': 'u'
                       },
                       {'name': 'v',
                        'type': 10,
                        'length': 80,
                        'precision': 0,
                        'expression': 'v'
                       },
                       {'name': 'deg',
                        'type': 6,
                        'length': 23,
                        'precision': 15,
                        'expression': 'deg'
                       },
                       {'name': 'deg_sc',
                        'type': 6,
                        'length': 23,
                        'precision': 15,
                        'expression': 'deg_sc'
                       },
                       {'name': 'landmark_s',
                        'type': 6,
                        'length': 23,
                        'precision': 15,
                        'expression': 'if(landmark_s IS NOT NULL, landmark_weight * deg, deg)'
                       }],
    'OUTPUT' : path_to_output_4
}
res4 = processing.run('qgis:refactorfields', paramsRefactor, feedback=feedback)


#-----------DIJKSTRA COMPUTATION-------------------------------------------

#change os.path and log
os.chdir('/home/b_kar02/UNI/routing/street_network/')
os.getcwd()

# Set origin destination pairs
origDestPairs = [
	{ 
		'name': 'A',
		'origin': (405827.45926481898641214,5756867.44089723471552134),
		'destination': (404983.26354647224070504,5757705.46554319839924574)
	},
	{ 
		'name': 'B',
		'origin': (406386.38577472395263612,5757094.12544078286737204),
		'destination': (405655.97231008461676538,5757699.92316147685050964)
	},
	{
		'name': 'C',
		'origin': (405780.46139126195339486,5758007.64649869874119759),
		'destination': (404885.32496485864976421,5757887.00421706214547157)
	}
]
# Create nx.graph from shapefile
Graph=nx.Graph(nx.read_shp(res4['OUTPUT'], strict=False, geom_attrs=True))

# create result array for pathes
resultPathes=[1,2,3]

out1=nx.Graph()
out2=nx.Graph()
out3=nx.Graph()

#compute pathes with dijkstra for all origin-destination pairs
for i in range(len(origDestPairs)):
    resultPathes[i] = nx.dijkstra_path(Graph,origDestPairs[i]['origin'],origDestPairs[i]['destination'], weight="landmark_s")
    print(resultPathes)
    print(len(resultPathes[i]))

#create nx pathes and save to shapefiles
for y in range(len(resultPathes[0])):
    out1.add_node(resultPathes[0][y])
    if y < (len(resultPathes[0])-1):
        out1.add_edge(resultPathes[0][y],resultPathes[0][y+1])
nx.write_shp(out1,'computedRoutes1')
for y in range(len(resultPathes[1])):
    out2.add_node(resultPathes[1][y])
    if y < (len(resultPathes[1])-1):
        out2.add_edge(resultPathes[1][y],resultPathes[1][y+1])
nx.write_shp(out2,'computedRoutes2')
for y in range(len(resultPathes[2])):
    out3.add_node(resultPathes[2][y])
    if y < (len(resultPathes[2])-1):
        out3.add_edge(resultPathes[2][y],resultPathes[2][y+1])
nx.write_shp(out3,'computedRoutes3')

#------- POSTPROCESSING TRNSLATION TO PRIMAL GRAPH AND POLYLINE CREATION--------------------------------------------------
# Create QGIS Layers from computed routes
computed_1 = QgsVectorLayer(path_computed_1, "Computed1", "ogr")
computed_1.setCrs(QgsCoordinateReferenceSystem(3044, QgsCoordinateReferenceSystem.EpsgCrsId))

computed_2 = QgsVectorLayer(path_computed_2, "Computed2", "ogr")
computed_2.setCrs(QgsCoordinateReferenceSystem(3044, QgsCoordinateReferenceSystem.EpsgCrsId))

computed_3 = QgsVectorLayer(path_computed_3, "Computed1", "ogr")
computed_3.setCrs(QgsCoordinateReferenceSystem(3044, QgsCoordinateReferenceSystem.EpsgCrsId))

# Create QGIS Layers from dual nodes
nodesDual = QgsVectorLayer(path_dual_nodes, "DualNodes", "ogr")
nodesDual.setCrs(QgsCoordinateReferenceSystem(3044, QgsCoordinateReferenceSystem.EpsgCrsId))

# For each route extract all dual nodes that are intersected by the pathes
paramsEqualNodesDual1 = { 
    'INPUT' : nodesDual,
    'PREDICATE' : 3,
    'INTERSECT' : computed_1,
    'output' : path_to_output_51,
}
feedback = QgsProcessingFeedback()
res51 = processing.run('native:extractbylocation', paramsEqualNodesDual1, feedback=feedback)

paramsEqualNodesDual2 = { 
    'INPUT' : nodesDual,
    'PREDICATE' : 3,
    'INTERSECT' : computed_2,
    'output' : path_to_output_52,
}
feedback = QgsProcessingFeedback()
res52 = processing.run('native:extractbylocation', paramsEqualNodesDual2, feedback=feedback)

paramsEqualNodesDual3 = { 
    'INPUT' : nodesDual,
    'PREDICATE' : 3,
    'INTERSECT' : computed_3,
    'output' : path_to_output_53,
}
feedback = QgsProcessingFeedback()
res53 = processing.run('native:extractbylocation', paramsEqualNodesDual3, feedback=feedback)



primal_edges = QgsVectorLayer(path_to_primal_edges, "PrimalEdges", "ogr")
primal_edges.setCrs(QgsCoordinateReferenceSystem(3044, QgsCoordinateReferenceSystem.EpsgCrsId))
dualPath1 = QgsVectorLayer(res51['OUTPUT'], "DualPath1", "ogr")
dualPath1.setCrs(QgsCoordinateReferenceSystem(3044,QgsCoordinateReferenceSystem.EpsgCrsId))
dualPath2 = QgsVectorLayer(res52['OUTPUT'], "DualPath2", "ogr")
dualPath2.setCrs(QgsCoordinateReferenceSystem(3044,QgsCoordinateReferenceSystem.EpsgCrsId))
dualPath3 = QgsVectorLayer(res53['OUTPUT'], "DualPath3", "ogr")
dualPath3.setCrs(QgsCoordinateReferenceSystem(3044,QgsCoordinateReferenceSystem.EpsgCrsId))

# Join StreetID of primal edges with streetIDs from dual nodes 
paramsJoin1 = { 
    'INPUT' : primal_edges,
    'FIELD' : 'streetID',
    'INPUT_2' : dualPath1,
    'FIELD_2' : 'streetID',
    'METHOD' : 0,
    'PREFIX' : 's',
    'output' : path_to_output_61,
}
feedback = QgsProcessingFeedback()
res61 = processing.run('native:joinattributestable', paramsJoin1, feedback=feedback)

paramsJoin2 = { 
    'INPUT' : primal_edges,
    'FIELD' : 'streetID',
    'INPUT_2' : dualPath2,
    'FIELD_2' : 'streetID',
    'METHOD' : 0,
    'PREFIX' : 's',
    'output' : path_to_output_62,
}
feedback = QgsProcessingFeedback()
res62 = processing.run('native:joinattributestable', paramsJoin2, feedback=feedback)

paramsJoin3 = { 
    'INPUT' : primal_edges,
    'FIELD' : 'streetID',
    'INPUT_2' : dualPath3,
    'FIELD_2' : 'streetID',
    'METHOD' : 0,
    'PREFIX' : 's',
    'output' : path_to_output_63,
}
feedback = QgsProcessingFeedback()
res63 = processing.run('native:joinattributestable', paramsJoin3, feedback=feedback)

# Extract only edges that are part of computed path
paramsExpr1 = { 
    'INPUT' : res61['OUTPUT'],
    'EXPRESSION' : "sstreetID IS NOT NULL", 
    'output' : path_to_output_71,
}
feedback = QgsProcessingFeedback()
res71 = processing.run('native:extractbyexpression', paramsExpr1, feedback=feedback)


paramsExpr2 = { 
    'INPUT' : res62['OUTPUT'],
    'EXPRESSION' : "sstreetID IS NOT NULL", 
    'output' : path_to_output_72,
}
feedback = QgsProcessingFeedback()
res72 = processing.run('native:extractbyexpression', paramsExpr2, feedback=feedback)


paramsExpr3 = { 
    'INPUT' : res63['OUTPUT'],
    'EXPRESSION' : "sstreetID IS NOT NULL", 
    'output' : path_to_output_73,
}
feedback = QgsProcessingFeedback()
res73 = processing.run('native:extractbyexpression', paramsExpr3, feedback=feedback)
 

# Create polyline from edges
paramsPoly1 = { 
    'input' : res71['OUTPUT'],
    'cats' : 2, 
    'type' : 0,
    'output' : path_to_output_81,
    'GRASS_OUTPUT_TYPE_PARAMETER' : 2
}
feedback = QgsProcessingFeedback()
res81 = processing.run('grass7:v.build.polylines', paramsPoly1, feedback=feedback)


paramsPoly2 = { 
    'input' : res72['OUTPUT'],
    'cats' : 2, 
    'type' : 0,
    'output' : path_to_output_82,
    'GRASS_OUTPUT_TYPE_PARAMETER' : 2
}
feedback = QgsProcessingFeedback()
res82 = processing.run('grass7:v.build.polylines', paramsPoly2, feedback=feedback)

paramsPoly3 = { 
    'input' : res73['OUTPUT'],
    'cats' : 2, 
    'type' : 0,
    'output' : path_to_output_83,
    'GRASS_OUTPUT_TYPE_PARAMETER' : 2
}
feedback = QgsProcessingFeedback()
res83 = processing.run('grass7:v.build.polylines', paramsPoly3, feedback=feedback)


