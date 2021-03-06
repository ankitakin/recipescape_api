from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.shortcuts import get_object_or_404, get_list_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from recipe_api.models import Clustering
from recipe_api.serializers import ClusteringSerializer, RecipeSerializer
from recipe_api.utils import tree_util
from tagger_api.models import Recipe, Annotation


@api_view(['GET'])
def get_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, origin_id=recipe_id)
    serializer = RecipeSerializer(recipe, many=False)
    return Response(serializer.data)


@cache_page(600)
@api_view(['GET'])
def get_recipes(request, dish):
    """
    Return all recipes for given dish
    :param dish: Kind of recipe (e.g chocolate cookie, potato salad)
    """
    recipes = Recipe.objects.filter(group_name=dish, annotation__isnull=False)
    serializer = RecipeSerializer(recipes, many=True)
    return Response(serializer.data)


@cache_page(600)
@api_view(['GET'])
def get_clusters(request, dish):
    """
    Return all clusters for given dish
    :param dish: Kind of recipe (e.g chocolate cookie, potato salad)
    """
    clusters = get_list_or_404(Clustering, dish_name=dish)
    serializer = ClusteringSerializer(clusters, many=True)
    return Response(serializer.data)


@cache_page(600)
@api_view(['POST'])
def get_trees_by_ids(request):
    """
    :param request:
    :param recipe_id: origin_id of Recipe model
    :return: [(action, [ingredient])]
    """
    recipe_ids = request.data['recipe_ids']
    annotations = Annotation.objects.filter(recipe__origin_id__in=recipe_ids).select_related('recipe')
    trees = [{
        'id': annotation.recipe.origin_id,
        'tree': tree_util.make_tree(annotation.recipe, annotation)
    } for annotation in annotations]
    return Response(trees)


@api_view(['GET'])
def get_trees(request, dish):
    annotations = _get_annotations_by_dish(dish)
    trees = [{
        'id': annotation.recipe.origin_id,
        'tree': tree_util.make_tree(annotation.recipe, annotation)
    } for annotation in annotations]
    return Response(trees)


@api_view(['GET'])
def get_nodes(request, dish):
    """
    Return list of action and ingredients for each recipe
    """
    annotations = _get_annotations_by_dish(dish)
    nodes = []
    for annotation in annotations:
        node = tree_util.make_node(annotation.recipe, annotation)
        nodes.append({'id': annotation.recipe.origin_id, 'actions': node['actions'], 'ingredients': node['ingredients']})
    return Response(nodes)


@api_view(['POST'])
def get_nodes_by_ids(request):
    recipe_ids = request.data['recipe_ids']
    annotations = Annotation.objects.filter(recipe__origin_id__in=recipe_ids).select_related('recipe')
    nodes = []
    for annotation in annotations:
        node = tree_util.make_node(annotation.recipe, annotation)
        nodes.append({'id': annotation.recipe.origin_id, 'actions': node['actions'], 'ingredients': node['ingredients']})
    return Response(nodes)


@cache_page(600)
@api_view(['POST'])
def get_histograms(request, dish):
    """
    For selected clusters,
    count distribution of top 3 actions and ingredients
    """
    trees, clusters, recipe_ids = _get_trees(dish, request.data['cluster_name'], request.data['selected_clusters'])
    analysis_result = tree_util.analyze_trees(trees, clusters, recipe_ids)
    return Response(analysis_result)


@api_view(['POST'])
def get_action_ingredient_histogram(request, dish):
    trees, clusters, recipe_ids= _get_trees(dish, request.data['cluster_name'], request.data['selected_clusters'])
    histogram = tree_util.count_tree_with_filter(trees, request.data['action'], request.data['ingredient'])
    return Response(histogram)


def _get_annotations_by_dish(dish):
    cache_key = 'annotation_' + dish
    annotations = cache.get(cache_key)
    if not annotations:
        annotations = Annotation.objects.filter(recipe__group_name=dish).select_related('recipe')
        cache.set(cache_key, annotations, 60 * 10)
    return annotations


def _get_trees(dish, cluster_name, selected_cluster):
    cluster = Clustering.objects.filter(dish_name__exact=dish, title__icontains=cluster_name).first()

    selected_ids = []
    id_cluster_dict = {}
    for p in cluster.points:
        if p['cluster_no'] in selected_cluster:
            selected_ids.append(p['recipe_id'])
            id_cluster_dict[p['recipe_id']] = p['cluster_no']

    annotations = _get_annotations_by_dish(dish)
    annotations_selected = [annotation for annotation in annotations
                            if annotation.recipe.origin_id in selected_ids]
    result = [(
        tree_util.make_tree(annotation.recipe, annotation), # tree
        id_cluster_dict[annotation.recipe.origin_id], # cluster
        annotation.recipe.origin_id, # recipe_id
    ) for annotation in annotations_selected]

    return zip(*result)
