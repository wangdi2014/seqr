"""
APIs used by the project page
"""

import itertools
import logging
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db.models import Q, Count

from settings import SEQR_ID_TO_MME_ID_MAP
from seqr.models import Family, Individual, _slugify, VariantTagType, VariantTag, VariantFunctionalData, AnalysisGroup
from seqr.utils.es_utils import is_nested_genotype_index
from seqr.views.apis.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.apis.individual_api import export_individuals
from seqr.views.apis.locus_list_api import get_sorted_project_locus_lists
from seqr.views.utils.json_utils import create_json_response
from seqr.views.utils.orm_to_json_utils import \
    _get_json_for_project, get_json_for_sample_dict, _get_json_for_families, _get_json_for_individuals, \
    get_json_for_saved_variants, get_json_for_analysis_groups, get_json_for_variant_functional_data_tag_types


from seqr.views.utils.permissions_utils import get_project_and_check_permissions
from xbrowse_server.mall import get_project_datastore
from xbrowse_server.base.models import Project as BaseProject

logger = logging.getLogger(__name__)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def project_page_data(request, project_guid):
    """Returns a JSON object containing information used by the project page:
    ::

      json_response = {
         'project': {..},
         'familiesByGuid': {..},
         'individualsByGuid': {..},
         'samplesByGuid': {..},
       }

    Args:
        project_guid (string): GUID of the Project to retrieve data for.
    """
    project = get_project_and_check_permissions(project_guid, request.user)

    families_by_guid, individuals_by_guid, samples_by_guid, analysis_groups_by_guid, locus_lists_by_guid = get_project_child_entities(project, request.user)

    project_json = _get_json_for_project(project, request.user)
    project_json['collaborators'] = _get_json_for_collaborator_list(project)
    project_json.update(_get_json_for_variant_tag_types(project, request.user, individuals_by_guid))
    project_json['locusListGuids'] = locus_lists_by_guid.keys()

    # gene search will be deprecated once the new database is online.
    project_json['hasGeneSearch'] = _has_gene_search(project)
    # TODO once all project data is reloaded get rid of this
    sorted_es_samples = sorted(
        [sample for sample in samples_by_guid.values() if sample['elasticsearchIndex']],
        key=lambda sample: sample['loadedDate'], reverse=True
    )
    project_json['hasNewSearch'] = sorted_es_samples and is_nested_genotype_index(sorted_es_samples[0]['elasticsearchIndex'])
    project_json['detailsLoaded'] = True

    return create_json_response({
        'projectsByGuid': {project_guid: project_json},
        'familiesByGuid': families_by_guid,
        'individualsByGuid': individuals_by_guid,
        'samplesByGuid': samples_by_guid,
        'locusListsByGuid': locus_lists_by_guid,
        'analysisGroupsByGuid': analysis_groups_by_guid,
        'matchmakerSubmissions': {project.guid: _project_matchmaker_submissions(project)},
    })


def get_project_child_entities(project, user):
    families_by_guid = _retrieve_families(project.guid, user)
    individuals_by_guid = _retrieve_individuals(project.guid, user)
    for individual_guid, individual in individuals_by_guid.items():
        families_by_guid[individual['familyGuid']]['individualGuids'].add(individual_guid)
    samples_by_guid = _retrieve_samples(project.guid, individuals_by_guid)
    analysis_groups_by_guid = _retrieve_analysis_groups(project)
    locus_lists = get_sorted_project_locus_lists(project, user)
    locus_lists_by_guid = {locus_list['locusListGuid']: locus_list for locus_list in locus_lists}
    return families_by_guid, individuals_by_guid, samples_by_guid, analysis_groups_by_guid, locus_lists_by_guid


def _retrieve_families(project_guid, user):
    """Retrieves family-level metadata for the given project.

    Args:
        project_guid (string): project_guid
        user (Model): for checking permissions to view certain fields
    Returns:
        dictionary: families_by_guid
    """
    fields = Family._meta.json_fields + Family._meta.internal_json_fields
    family_models = Family.objects.filter(project__guid=project_guid).only(*fields)

    families = _get_json_for_families(family_models, user, project_guid=project_guid)

    families_by_guid = {}
    for family in families:
        family_guid = family['familyGuid']
        family['individualGuids'] = set()
        families_by_guid[family_guid] = family

    return families_by_guid


def _retrieve_individuals(project_guid, user):
    """Retrieves individual-level metadata for the given project.

    Args:
        project_guid (string): project_guid
    Returns:
        dictionary: individuals_by_guid
    """

    individual_models = Individual.objects.filter(family__project__guid=project_guid)

    individuals = _get_json_for_individuals(individual_models, user=user, project_guid=project_guid)

    individuals_by_guid = {}
    for i in individuals:
        i['sampleGuids'] = set()
        individual_guid = i['individualGuid']
        individuals_by_guid[individual_guid] = i

    return individuals_by_guid


def _retrieve_samples(project_guid, individuals_by_guid):
    """Retrieves sample metadata for the given project.

        Args:
            project_guid (string): project_guid
            individuals_by_guid (dict): maps each individual_guid to a dictionary with individual info.
                This method adds a "sampleGuids" list to each of these dictionaries.
        Returns:
            2-tuple with dictionaries: (samples_by_guid, sample_batches_by_guid)
        """
    # TODO use ORM  instead of raw query
    cursor = connection.cursor()

    # use raw SQL since the Django ORM doesn't have a good way to express these types of queries.
    sample_query = """
        SELECT
          p.guid AS project_guid,
          i.guid AS individual_guid,
          s.guid AS sample_guid,
          s.created_date AS sample_created_date,
          s.sample_type AS sample_sample_type,
          s.dataset_type AS sample_dataset_type,
          s.sample_id AS sample_sample_id,
          s.elasticsearch_index AS sample_elasticsearch_index,
          s.dataset_file_path AS sample_dataset_file_path,
          s.sample_status AS sample_sample_status,
          s.loaded_date AS sample_loaded_date
        FROM seqr_sample AS s
          JOIN seqr_individual AS i ON s.individual_id=i.id
          JOIN seqr_family AS f ON i.family_id=f.id
          JOIN seqr_project AS p ON f.project_id=p.id
        WHERE p.guid=%s
    """.strip()

    cursor.execute(sample_query, [project_guid])

    columns = [col[0] for col in cursor.description]

    samples_by_guid = {}
    for row in cursor.fetchall():
        record = dict(zip(columns, row))

        sample_guid = record['sample_guid']
        if sample_guid not in samples_by_guid:
            samples_by_guid[sample_guid] = get_json_for_sample_dict(record)

        individual_guid = record['individual_guid']
        individuals_by_guid[individual_guid]['sampleGuids'].add(sample_guid)

        samples_by_guid[sample_guid]['individualGuid'] = individual_guid

    cursor.close()

    return samples_by_guid


def _retrieve_analysis_groups(project):
    group_models = AnalysisGroup.objects.filter(project=project)
    groups = get_json_for_analysis_groups(group_models, project_guid=project.guid)
    return {group['analysisGroupGuid']: group for group in groups}


def _get_json_for_collaborator_list(project):
    """Returns a JSON representation of the collaborators in the given project"""
    collaborator_list = []

    def _compute_json(collaborator, can_view, can_edit):
        return {
            'displayName': collaborator.profile.display_name,
            'username': collaborator.username,
            'email': collaborator.email,
            'firstName': collaborator.first_name,
            'lastName': collaborator.last_name,
            'hasViewPermissions': can_view,
            'hasEditPermissions': can_edit,
        }

    previously_added_ids = set()
    for collaborator in itertools.chain(project.owners_group.user_set.all(), project.can_edit_group.user_set.all()):
        if collaborator.id in previously_added_ids:
            continue
        previously_added_ids.add(collaborator.id)
        collaborator_list.append(
            _compute_json(collaborator, can_edit=True, can_view=True)
        )
    for collaborator in project.can_view_group.user_set.all():
        if collaborator.id in previously_added_ids:
            continue
        previously_added_ids.add(collaborator.id)
        collaborator_list.append(
            _compute_json(collaborator, can_edit=False, can_view=True)
        )

    return sorted(collaborator_list, key=lambda collaborator: (collaborator['lastName'], collaborator['displayName']))


def _get_json_for_variant_tag_types(project, user, individuals_by_guid):
    individual_guids_by_id = {
        individual['individualId']: individual_guid for individual_guid, individual in individuals_by_guid.items()
    }

    tag_counts_by_type_and_family = VariantTag.objects.filter(saved_variant__project=project).values('saved_variant__family__guid', 'variant_tag_type__name').annotate(count=Count('*'))
    project_variant_tags = get_project_variant_tag_types(project, tag_counts_by_type_and_family=tag_counts_by_type_and_family)
    discovery_tags = []
    for tag_type in project_variant_tags:
        if tag_type['category'] == 'CMG Discovery Tags' and tag_type['numTags'] > 0:
            tags = VariantTag.objects.filter(saved_variant__project=project, variant_tag_type__guid=tag_type['variantTagTypeGuid']).select_related('saved_variant')
            saved_variants = [tag.saved_variant for tag in tags]
            discovery_tags += get_json_for_saved_variants(
                saved_variants, add_tags=True, add_details=True, project=project, user=user, individual_guids_by_id=individual_guids_by_id)

    project_functional_tags = []
    for category, tags in VariantFunctionalData.FUNCTIONAL_DATA_CHOICES:
        project_functional_tags += [{
            'category': category,
            'name': name,
            'metadataTitle': json.loads(tag_json).get('metadata_title'),
            'color': json.loads(tag_json)['color'],
            'description': json.loads(tag_json).get('description'),
        } for name, tag_json in tags]

    return {
        'variantTagTypes': sorted(project_variant_tags, key=lambda variant_tag_type: variant_tag_type['order']),
        'variantFunctionalTagTypes': get_json_for_variant_functional_data_tag_types(),
        'discoveryTags': discovery_tags,
    }


def get_project_variant_tag_types(project, tag_counts_by_type_and_family=None):
    project_variant_tags = []
    for variant_tag_type in VariantTagType.objects.filter(Q(project=project) | Q(project__isnull=True)):
        tag_type = {
            'variantTagTypeGuid': variant_tag_type.guid,
            'name': variant_tag_type.name,
            'category': variant_tag_type.category,
            'description': variant_tag_type.description,
            'color': variant_tag_type.color,
            'order': variant_tag_type.order,
            'is_built_in': variant_tag_type.is_built_in,
        }
        if tag_counts_by_type_and_family is not None:
            current_tag_type_counts = [counts for counts in tag_counts_by_type_and_family if
                                       counts['variant_tag_type__name'] == variant_tag_type.name]
            num_tags = sum(count['count'] for count in current_tag_type_counts)
            tag_type.update({
                'numTags': num_tags,
                'numTagsPerFamily': {count['saved_variant__family__guid']: count['count'] for count in
                                     current_tag_type_counts},
            })
        project_variant_tags.append(tag_type)

    return sorted(project_variant_tags, key=lambda variant_tag_type: variant_tag_type['order'])


"""
def _get_json_for_reference_populations(project):
    result = []

    for reference_populations in project.custom_reference_populations.all():
        result.append({
            'id': reference_populations.slug,
            'name': reference_populations.name,
        })

    return result
"""


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def export_project_individuals_handler(request, project_guid):
    """Export project Individuals table.

    Args:
        project_guid (string): GUID of the project for which to export individual data
    """

    format = request.GET.get('file_format', 'tsv')
    include_phenotypes = bool(request.GET.get('include_phenotypes'))

    project = get_project_and_check_permissions(project_guid, request.user)

    # get all individuals in this project
    individuals = Individual.objects.filter(family__project=project).order_by('family__family_id', 'affected')

    filename_prefix = "%s_individuals" % _slugify(project.name)

    return export_individuals(
        filename_prefix,
        individuals,
        format,
        include_hpo_terms_present=include_phenotypes,
        include_hpo_terms_absent=include_phenotypes,
    )


def _has_gene_search(project):
    """
    Returns True if this project has Gene Search enabled.

    DEPRECATED - will be removed along with mongodb.

    Args:
         project (object): django project
    """
    try:
        base_project = BaseProject.objects.get(seqr_project=project)
    except ObjectDoesNotExist as e:
        return False

    return base_project.has_elasticsearch_index() or get_project_datastore(base_project).project_collection_is_loaded(base_project)


def _project_matchmaker_submissions(project):
    submissions_by_individual = {}
    for submission in SEQR_ID_TO_MME_ID_MAP.find({'project_id': project.deprecated_project_id}):
        individual_submission = submissions_by_individual.get(submission['seqr_id'])
        if not individual_submission or individual_submission['submissionDate'] < submission['insertion_date']:
            individual_submission = {
                'submissionDate': submission['insertion_date'],
                'projectId': submission['project_id'],
                'familyId': submission['family_id'],
                'individualId': submission['seqr_id'],
                'submittedData': submission['submitted_data'],
            }
            if submission.get('deletion'):
                deleted_by = User.objects.filter(username=submission['deletion']['by']).first()
                individual_submission['deletion'] = {
                    'date': submission['deletion']['date'],
                    'by': (deleted_by.get_full_name() or deleted_by.email) if deleted_by else submission['deletion']['by'],
                }
        submissions_by_individual[submission['seqr_id']] = individual_submission
    return submissions_by_individual
