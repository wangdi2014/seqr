"""seqr URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
"""
from seqr.views.react_app import main_app
from seqr.views.apis.dataset_api import add_dataset_handler
from settings import ENABLE_DJANGO_DEBUG_TOOLBAR
from django.conf.urls import url, include

from seqr.views.apis.family_api import \
    update_family_fields_handler, \
    edit_families_handler, \
    delete_families_handler, \
    update_family_analysed_by, \
    receive_families_table_handler

from seqr.views.apis.individual_api import \
    update_individual_handler, \
    edit_individuals_handler, \
    delete_individuals_handler, \
    receive_individuals_table_handler, \
    save_individuals_table_handler

from seqr.views.apis.phenotips_api import \
    proxy_to_phenotips, \
    phenotips_pdf_handler, \
    phenotips_edit_handler, \
    receive_hpo_table_handler, \
    update_individual_hpo_terms

from seqr.views.apis.case_review_api import \
    save_internal_case_review_notes, \
    save_internal_case_review_summary

from seqr.views.apis.saved_variant_api import \
    saved_variant_data, \
    create_saved_variant_handler, \
    update_variant_tags_handler, \
    create_variant_note_handler, \
    update_variant_note_handler, \
    delete_variant_note_handler, \
    update_saved_variant_json

from seqr.views.pages.dashboard_page import \
    dashboard_page_data, \
    export_projects_table_handler

from seqr.views.pages.project_page import \
    project_page_data, \
    export_project_individuals_handler

from seqr.views.apis.gene_api import \
    gene_info, \
    genes_info, \
    create_gene_note_handler, \
    update_gene_note_handler, \
    delete_gene_note_handler

from seqr.views.pages.staff.staff_pages import \
    seqr_stats_page, \
    users_page, proxy_to_kibana, kibana_page

from seqr.views.apis.locus_list_api import \
    locus_lists, \
    locus_list_info, \
    create_locus_list_handler, \
    update_locus_list_handler, \
    delete_locus_list_handler, \
    add_project_locus_lists, \
    delete_project_locus_lists

from seqr.views.apis.variant_search_api import \
    query_variants_handler, \
    query_single_variant_handler, \
    search_context_handler, \
    export_variants_handler, \
    get_saved_search_handler, \
    create_saved_search_handler

from seqr.views.apis.staff_api import anvil_export, discovery_sheet, get_projects_for_category
from seqr.views.pages.staff.elasticsearch_status import elasticsearch_status
from seqr.views.pages.staff.komp_export import komp_export

from seqr.views.apis.awesomebar_api import awesomebar_autocomplete_handler
from seqr.views.apis.auth_api import login_required_error, API_LOGIN_REQUIRED_URL
from seqr.views.apis.igv_api import fetch_igv_track
from seqr.views.apis.analysis_group_api import update_analysis_group_handler, delete_analysis_group_handler
from seqr.views.apis.project_api import create_project_handler, update_project_handler, delete_project_handler
from seqr.views.apis.project_categories_api import update_project_categories_handler
from seqr.views.utils.file_utils import save_temp_file

react_app_pages = [
    r'^$',
    'dashboard',
    'project/(?P<project_guid>[^/]+)/.*',
    'gene_info/.*',
    'gene_lists/.*',
    'variant_search/.*',
    'staff/.*',
]

# NOTE: the actual url will be this with an '/api' prefix
api_endpoints = {
    'individual/(?P<individual_guid>[\w.|-]+)/update': update_individual_handler,
    'individual/(?P<individual_guid>[\w.|-]+)/update_hpo_terms': update_individual_hpo_terms,

    'family/(?P<family_guid>[\w.|-]+)/save_internal_case_review_notes': save_internal_case_review_notes,
    'family/(?P<family_guid>[\w.|-]+)/save_internal_case_review_summary': save_internal_case_review_summary,
    'family/(?P<family_guid>[\w.|-]+)/update': update_family_fields_handler,
    'family/(?P<family_guid>[\w.|-]+)/update_analysed_by': update_family_analysed_by,

    'dashboard': dashboard_page_data,
    'dashboard/export_projects_table': export_projects_table_handler,

    'project/(?P<project_guid>[^/]+)/details': project_page_data,
    'project/(?P<project_guid>[^/]+)/export_project_individuals': export_project_individuals_handler,

    'project/create_project': create_project_handler,
    'project/(?P<project_guid>[^/]+)/update_project': update_project_handler,
    'project/(?P<project_guid>[^/]+)/delete_project': delete_project_handler,
    'project/(?P<project_guid>[^/]+)/update_project_categories': update_project_categories_handler,

    'project/(?P<project_guid>[^/]+)/saved_variants/(?P<variant_guid>[^/]+)?': saved_variant_data,

    'project/(?P<project_guid>[^/]+)/edit_families': edit_families_handler,
    'project/(?P<project_guid>[^/]+)/delete_families': delete_families_handler,
    'project/(?P<project_guid>[^/]+)/edit_individuals': edit_individuals_handler,
    'project/(?P<project_guid>[^/]+)/delete_individuals': delete_individuals_handler,
    'project/(?P<project_guid>[^/]+)/upload_families_table': receive_families_table_handler,

    'project/(?P<project_guid>[^/]+)/upload_individuals_table': receive_individuals_table_handler,
    'project/(?P<project_guid>[^/]+)/save_individuals_table/(?P<upload_file_id>[^/]+)': save_individuals_table_handler,
    'project/(?P<project_guid>[^/]+)/add_dataset': add_dataset_handler,

    'project/(?P<project_guid>[^/]+)/igv_track/(?P<igv_track_path>.+)': fetch_igv_track,
    'project/(?P<project_guid>[^/]+)/individual/(?P<individual_guid>[\w.|-]+)/phenotips_pdf': phenotips_pdf_handler,
    'project/(?P<project_guid>[^/]+)/individual/(?P<individual_guid>[\w.|-]+)/phenotips_edit': phenotips_edit_handler,
    'project/(?P<project_guid>[^/]+)/upload_hpo_terms_table': receive_hpo_table_handler,

    'project/(?P<project_guid>[^/]+)/analysis_groups/create': update_analysis_group_handler,
    'project/(?P<project_guid>[^/]+)/analysis_groups/(?P<analysis_group_guid>[^/]+)/update': update_analysis_group_handler,
    'project/(?P<project_guid>[^/]+)/analysis_groups/(?P<analysis_group_guid>[^/]+)/delete': delete_analysis_group_handler,
    'project/(?P<project_guid>[^/]+)/update_saved_variant_json': update_saved_variant_json,

    'search/variant/(?P<variant_id>[^/]+)': query_single_variant_handler,
    'search/(?P<search_hash>[^/]+)': query_variants_handler,
    'search/(?P<search_hash>[^/]+)/download': export_variants_handler,
    'search_context': search_context_handler,
    'saved_search/all': get_saved_search_handler,
    'saved_search/create': create_saved_search_handler,

    'saved_variant/create': create_saved_variant_handler,
    'saved_variant/(?P<variant_guid>[^/]+)/update_tags': update_variant_tags_handler,
    'saved_variant/(?P<variant_guid>[^/]+)/note/create': create_variant_note_handler,
    'saved_variant/(?P<variant_guid>[^/]+)/note/(?P<note_guid>[^/]+)/update': update_variant_note_handler,
    'saved_variant/(?P<variant_guid>[^/]+)/note/(?P<note_guid>[^/]+)/delete': delete_variant_note_handler,

    'genes_info': genes_info,
    'gene_info/(?P<gene_id>[^/]+)': gene_info,
    'gene_info/(?P<gene_id>[^/]+)/note/create': create_gene_note_handler,
    'gene_info/(?P<gene_id>[^/]+)/note/(?P<note_guid>[^/]+)/update': update_gene_note_handler,
    'gene_info/(?P<gene_id>[^/]+)/note/(?P<note_guid>[^/]+)/delete': delete_gene_note_handler,

    'locus_lists': locus_lists,
    'locus_lists/(?P<locus_list_guid>[^/]+)': locus_list_info,
    'locus_lists/create': create_locus_list_handler,
    'locus_lists/(?P<locus_list_guid>[^/]+)/update': update_locus_list_handler,
    'locus_lists/(?P<locus_list_guid>[^/]+)/delete': delete_locus_list_handler,
    'project/(?P<project_guid>[^/]+)/add_locus_lists': add_project_locus_lists,
    'project/(?P<project_guid>[^/]+)/delete_locus_lists': delete_project_locus_lists,

    'awesomebar': awesomebar_autocomplete_handler,

    'upload_temp_file': save_temp_file,

    'staff/anvil/(?P<project_guid>[^/]+)': anvil_export,
    'staff/discovery_sheet/(?P<project_guid>[^/]+)': discovery_sheet,
    'staff/projects_for_category/(?P<project_category_name>[^/]+)': get_projects_for_category,

}

urlpatterns = []

phenotips_urls = '^(?:%s)' % ('|'.join([
    'ssx', 'skin', 'skins', 'get', 'lock', 'preview', 'download', 'export',
    'XWiki', 'cancel', 'resources', 'rollback', 'rest', 'webjars', 'bin', 'jsx'
]))

urlpatterns += [
    url(phenotips_urls, proxy_to_phenotips, name='proxy_to_phenotips'),
]

# core react page templates
urlpatterns += [url("^%(url_endpoint)s$" % locals(), main_app) for url_endpoint in react_app_pages]

# api
for url_endpoint, handler_function in api_endpoints.items():
    urlpatterns.append( url("^api/%(url_endpoint)s$" % locals(), handler_function) )

# login redirect for ajax calls
urlpatterns += [
    url(API_LOGIN_REQUIRED_URL.lstrip('/'), login_required_error)
]

#urlpatterns += [
#   url("^api/v1/%(url_endpoint)s$" % locals(), handler_function) for url_endpoint, handler_function in api_endpoints.items()]

kibana_urls = '^(?:%s)' % ('|'.join([
    "app", "bundles", "elasticsearch", "plugins", "ui", "api/apm", "api/console", "api/index_management", "api/index_patterns",
    "api/kibana", "api/monitoring", "api/reporting", "api/saved_objects", "api/telemetry", "api/timelion", "api/xpack",
    "es_admin",
]))

urlpatterns += [
    url(kibana_urls, proxy_to_kibana, name='proxy_to_kibana'),
]


# other staff-only endpoints
urlpatterns = [
    url("^staff/seqr_stats/?", seqr_stats_page, name="seqr_stats"),
    url("^staff/elasticsearch_status", elasticsearch_status, name="elasticsearch_status"),
    url("^staff/komp_export", komp_export, name="komp_export"),
    url("^staff/users/?", users_page, name="users_page"),
    url("^staff/kibana/?", kibana_page, name="kibana_page"),
] + urlpatterns

urlpatterns += [
    url(r'^hijack/', include('hijack.urls')),
]

# django debug toolbar
if ENABLE_DJANGO_DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
