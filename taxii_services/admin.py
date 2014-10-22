# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

import models

from django.contrib import admin


class DataCollectionAdmin(admin.ModelAdmin):
    filter_vertical = ("supported_content", )
    # TODO: make checking 'accept all content' disable the supported content selector
    pass


class InboxServiceAdmin(admin.ModelAdmin):
    filter_vertical = ("supported_content", )
    # TODO: make checking 'accept all content' disable the supported content selector
    fieldsets = (
        (None, {
            'classes': ('wide', ),
            'fields': ('name', 'path', 'description', 'supported_message_bindings', 'supported_protocol_bindings', 'inbox_message_handler', 'enabled', 'accept_all_content', 'supported_content',)
        }),
        ('Destination Collection Options', {
            # 'classes': ('collapse', ),
            'fields': ('destination_collection_status', 'destination_collections', )
        })
    )


class InboxMessageAdmin(admin.ModelAdmin):
    readonly_fields = ('message_id', 'sending_ip', 'result_id',
                       'record_count', 'partial_count', 'collection_name',
                       'subscription_id', 'exclusive_begin_timestamp_label',
                       'inclusive_end_timestamp_label', 'received_via',
                       'original_message', 'content_block_count', 'content_blocks_saved')


class DiscoveryServiceAdmin(admin.ModelAdmin):
    pass


class PollServiceAdmin(admin.ModelAdmin):
    pass


class CollectionManagementServiceAdmin(admin.ModelAdmin):
    pass


class ProtocolBindingAdmin(admin.ModelAdmin):
    pass


class MessageBindingAdmin(admin.ModelAdmin):
    pass


class ContentBindingSubtypeInline(admin.TabularInline):
    model = models.ContentBindingSubtype


class ContentBindingAdmin(admin.ModelAdmin):
    # list_display = ['name', 'description', 'id', 'binding_id', 'date_created', 'date_updated']
    inlines = [ContentBindingSubtypeInline]


class ContentBlockAdmin(admin.ModelAdmin):
    pass


class ValidatorAdmin(admin.ModelAdmin):
    pass


class ResultSetPartInline(admin.TabularInline):
    model = models.ResultSetPart


class ResultSetAdmin(admin.ModelAdmin):
    inlines = [ResultSetPartInline]


class QueryScopeInline(admin.TabularInline):
    model = models.QueryScope


class SupportedQueryAdmin(admin.ModelAdmin):
    inlines = [QueryScopeInline]


class QueryHandlerAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'module_name', 'class_name',
                    'version']


class MessageHandlerAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'module_name', 'class_name', 'supported_messages', 'version']


def register_admins(admin_list=None):
    """
    This function registers all the model admins. This isn't done by default.
    """

    # TODO: Use the admin_list argument to register only specified admins or delete the argument

    admin.site.register(models.CollectionManagementService, CollectionManagementServiceAdmin)
    admin.site.register(models.ContentBinding, ContentBindingAdmin)
    admin.site.register(models.ContentBlock, ContentBlockAdmin)
    admin.site.register(models.DataCollection, DataCollectionAdmin)
    admin.site.register(models.DiscoveryService, DiscoveryServiceAdmin)
    admin.site.register(models.InboxMessage, InboxMessageAdmin)
    admin.site.register(models.InboxService, InboxServiceAdmin)
    admin.site.register(models.MessageBinding, MessageBindingAdmin)
    admin.site.register(models.PollService, PollServiceAdmin)
    admin.site.register(models.ProtocolBinding, ProtocolBindingAdmin)
    admin.site.register(models.ResultSet, ResultSetAdmin)
    # admin.site.register(models.ServiceHandler, ServiceHandlerAdmin)
    admin.site.register(models.Validator, ValidatorAdmin)

    admin.site.register(models.MessageHandler, MessageHandlerAdmin)

    # Query stuff - the be put into the alphabetized list later
    # admin.site.register(models.CapabilityModule, CapabilityModuleAdmin)
    # admin.site.register(models.TargetingExpression, TargetingExpressionAdmin)
    admin.site.register(models.SupportedQuery, SupportedQueryAdmin)
    admin.site.register(models.QueryHandler, QueryHandlerAdmin)
    # admin.site.register(models.QueryScope, QueryScopeAdmin)
