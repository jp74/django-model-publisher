
"""
    created 2017 by Jens Diemer <ya-publisher@jensdiemer.de>
"""

import sys
from unittest import mock

import django
from django.test.utils import override_settings

from cms.models import Page

from publisher.models import PublisherStateModel
from publisher_test_project.publisher_list_app.models import PublisherItem
from publisher_tests.base import ClientBaseTestCase


@override_settings(LOGGING={})
class PublisherItemAppTestCase(ClientBaseTestCase):
    """
    PublisherItem test instances made with:

    publisher_test_project.publisher_list_app.fixtures.list_item_fixtures()

    'reporter' user has not 'can_publish' -> can only create un-/publish requests
    'editor' user has 'can_publish' -> can publish and accept/reject un-/publish requests
    """
    @classmethod
    def setUpTestData(cls):
        super(PublisherItemAppTestCase, cls).setUpTestData()

        # $ ./publisher_test_project/manage.py cms_page_info application_urls application_namespace navigation_extenders

        list_page = Page.objects.public().get(application_namespace="PublisherItem")
        cls.list_page_url = list_page.get_absolute_url(language="en")

        def get_item(text):
            qs = PublisherItem.objects.translated("en", text=text).language("en")
            item = qs.get(publisher_is_draft=True) # used the draft version
            url = item.get_absolute_url(language="en")
            return item, url

        cls.not_published_item, cls.not_published_item_url = get_item("Not published Item")
        cls.published_item, cls.published_item_url = get_item("Published Item")
        cls.hidden_by_start_date_item, cls.hidden_by_start_date_item_url = get_item("hidden by start date")
        cls.hidden_by_end_date_item, cls.hidden_by_end_date_item_url = get_item("hidden by end date")
        cls.dirty_item, cls.dirty_item_url = get_item("This is dirty!")

    def get_admin_change_url(self, obj):
        assert obj.publisher_is_draft == True, "%s not draft!" % obj
        url = super(PublisherItemAppTestCase, self).get_admin_change_url(obj)
        url += "?language=en"
        return url

    def test_setUp(self):
        self.assertEqual(self.list_page_url, "/en/publisheritems/")

        self.assertEqual(self.not_published_item.slug, "not-published-item")
        self.assertEqual(self.not_published_item.is_published, False)
        self.assertEqual(self.not_published_item.hidden_by_end_date, False)
        self.assertEqual(self.not_published_item.hidden_by_start_date, False)
        self.assertEqual(self.not_published_item.is_visible, False)
        self.assertEqual(self.not_published_item.is_dirty, True)
        self.assertEqual(self.not_published_item_url, "/en/publisheritems/not-published-item/")

        self.assertEqual(self.published_item.slug, "published-item")
        self.assertEqual(self.published_item.is_published, False) # It's the draft, not the published instance
        self.assertEqual(self.published_item.hidden_by_end_date, False)
        self.assertEqual(self.published_item.hidden_by_start_date, False)
        self.assertEqual(self.published_item.is_visible, True)
        self.assertEqual(self.published_item.is_dirty, False)
        self.assertEqual(self.published_item_url, "/en/publisheritems/published-item/")

        self.assertEqual(self.hidden_by_start_date_item.slug, "hidden-by-start-date")
        self.assertEqual(self.hidden_by_start_date_item.is_published, False)
        self.assertEqual(self.hidden_by_start_date_item.hidden_by_end_date, False)
        self.assertEqual(self.hidden_by_start_date_item.hidden_by_start_date, True)
        self.assertEqual(self.hidden_by_start_date_item.is_visible, False)
        self.assertEqual(self.hidden_by_start_date_item.is_dirty, False)
        self.assertEqual(self.hidden_by_start_date_item_url, "/en/publisheritems/hidden-by-start-date/")

        self.assertEqual(self.hidden_by_end_date_item.slug, "hidden-by-end-date")
        self.assertEqual(self.hidden_by_end_date_item.is_published, False)
        self.assertEqual(self.hidden_by_end_date_item.hidden_by_end_date, True)
        self.assertEqual(self.hidden_by_end_date_item.hidden_by_start_date, False)
        self.assertEqual(self.hidden_by_end_date_item.is_visible, False)
        self.assertEqual(self.hidden_by_end_date_item.is_dirty, False)
        self.assertEqual(self.hidden_by_end_date_item_url, "/en/publisheritems/hidden-by-end-date/")

        self.assertEqual(self.dirty_item.slug, "dirty")
        self.assertEqual(self.dirty_item.is_published, False)
        self.assertEqual(self.dirty_item.hidden_by_end_date, False)
        self.assertEqual(self.dirty_item.hidden_by_start_date, False)
        self.assertEqual(self.dirty_item.is_visible, True)
        self.assertEqual(self.dirty_item.is_dirty, True)
        self.assertEqual(self.dirty_item_url, "/en/publisheritems/dirty/")

        url = self.get_admin_change_url(obj=self.published_item)
        if django.VERSION < (1, 11):
            self.assertEqual(url,
                "/en/admin/publisher_list_app/publisheritem/%i/?language=en" % self.published_item.pk
            )
        else:
            self.assertEqual(url,
                "/en/admin/publisher_list_app/publisheritem/%i/change/?language=en" % self.published_item.pk
            )

    #-------------------------------------------------------------------------

    def test_anonymous_list_item_page(self):
        response = self.client.get(self.list_page_url, HTTP_ACCEPT_LANGUAGE="en")
        self.assertResponse(response,
            must_contain=(
                "Publisher List App - list view",

                "/en/publisheritems/published-item/", "Published Item",
                "/en/publisheritems/dirty/", "dirty",
            ),
            must_not_contain=(
                "Error", "Traceback",
            ),
            status_code=200,
            template_name="list_app/list.html",
            html=False,
        )

    def test_anonymous_list_item_detail_page(self):
        response = self.client.get(self.published_item_url, HTTP_ACCEPT_LANGUAGE="en")
        self.assertResponse(response,
            must_contain=(
                "Publisher List App - detail view",

                "Published Item",
            ),
            must_not_contain=(
                "Error", "Traceback",
            ),
            status_code=200,
            template_name="list_app/detail.html",
            html=False,
        )

    #-------------------------------------------------------------------------

    def test_anonymous_hidden(self):
        response = self.client.get(self.not_published_item_url, HTTP_ACCEPT_LANGUAGE="en")
        # self.debug_response(response)
        self.assertResponse(response,
            must_contain=("Not Found",),
            must_not_contain=None,
            status_code=404,
            template_name=None,
            html=False,
            browser_traceback=True
        )

    #-------------------------------------------------------------------------

    def test_editor_edit_list_item_admin_view(self):
        self.login_editor_user()

        response = self.client.get(
            self.get_admin_change_url(obj=self.dirty_item),
            HTTP_ACCEPT_LANGUAGE="en"
        )
        # self.debug_response(response)

        # 'editor' user has 'can_publish' -> can publish and accept/reject un-/publish requests:

        self.assertResponse(response,
            must_contain=(
                "user 'editor'",
                "Change publisher item (English)",

                "Text:", "This is dirty!",
                "Slug:", "dirty",

                # publisher submit buttons:
                "_save", "Save draft",
                "_save_published", "Save and Publish",

                "Publisher History", "No changes, yet.",
            ),
            must_not_contain=(
                "_ask_publish", "Request Publishing",
                "_ask_unpublish", "Request Unpublishing",

                "send publish request",
                "Note:", # publisher note textarea

                "Error", "Traceback"
            ),
            status_code=200,
            template_name="publisher/parler/change_form.html",
            html=False,
        )

    def test_reporter_edit_list_item_admin_view(self):
        self.login_reporter_user()

        response = self.client.get(
            self.get_admin_change_url(obj=self.dirty_item),
            HTTP_ACCEPT_LANGUAGE="en"
        )
        # self.debug_response(response)

        # 'reporter' user has not 'can_publish' -> can only create un-/publish requests:

        self.assertResponse(response,
            must_contain=(
                "user 'reporter'",
                "Change publisher item (English)",

                "Text:", "This is dirty!",
                "Slug:", "dirty",

                # publisher submit buttons:

                "_ask_publish", "Request Publishing",
                "_ask_unpublish", "Request Unpublishing",

                "send publish request",
                "Note:", # publisher note textarea

                "Publisher History", "No changes, yet.",
            ),
            must_not_contain=(
                "_save", "Save draft",
                "_save_published", "Save and Publish",

                "Error", "Traceback"
            ),
            status_code=200,
            template_name="publisher/parler/change_form.html",
            html=False,
        )
    def test_reporter_changelist_admin_view(self):
        self.login_reporter_user()

        response = self.client.get(
            "/en/admin/publisher_list_app/publisheritem/",
            HTTP_ACCEPT_LANGUAGE="en"
        )
        # self.debug_response(response)

        # 'reporter' user has not 'can_publish' -> can only create un-/publish requests:

        self.assertResponse(response,
            must_contain=(
                "Django administration",

                "user 'reporter'",

                # FIXME: Check correct assignment:

                "This is dirty!", "Changes not yet published. Older version is online.",
                "hidden by end date", "Published, but hidden by end date.",
                "hidden by start date", "Published, but hidden by start date.",
                "Published Item", "Is public.",
                "Not published Item", "Not published, yet",

                "5 publisher items",
            ),
            must_not_contain=(
                "Error", "Traceback"
            ),
            status_code=200,
            template_name="admin/change_list.html",
            html=False,
        )

    def test_editor_list_page_view_no_edit(self):
        self.login_editor_user()

        response = self.client.get(
            self.list_page_url,
            HTTP_ACCEPT_LANGUAGE="en"
        )
        # self.debug_response(response)

        # 'editor' user has 'can_publish' -> can publish and accept/reject un-/publish requests:

        self.assertResponse(response,
            must_contain=(
                "user 'editor'",

                "Publisher List App - list view",

                "/en/publisheritems/published-item/", "Published Item",
                "/en/publisheritems/dirty/", "dirty",
            ),
            must_not_contain=(
                "/en/publisheritems/not-published-item", "Not published Item",
                "/en/publisheritems/hidden-by-start-date", "hidden by start date",
                "/en/publisheritems/hidden-by-end-date", "hidden by end date",

                "Error", "Traceback",
            ),
            status_code=200,
            template_name="list_app/list.html",
            html=False,
        )

    def test_editor_list_page_view_edit(self):
        self.login_editor_user()

        response = self.client.get(
            self.list_page_url + "?edit",
            HTTP_ACCEPT_LANGUAGE="en"
        )
        # self.debug_response(response)

        # 'editor' user has 'can_publish' -> can publish and accept/reject un-/publish requests:

        self.assertResponse(response,
            must_contain=(
                "user 'editor'",

                "Publisher List App - list view",

                "/en/publisheritems/not-published-item", "Not published Item",
                "/en/publisheritems/published-item", "Published Item",
                "/en/publisheritems/hidden-by-start-date", "hidden by start date",
                "/en/publisheritems/hidden-by-end-date", "hidden by end date",
                "/en/publisheritems/dirty", "This is dirty!",
            ),
            must_not_contain=(
                "Error", "Traceback",
            ),
            status_code=200,
            template_name="list_app/list.html",
            html=False,
        )
