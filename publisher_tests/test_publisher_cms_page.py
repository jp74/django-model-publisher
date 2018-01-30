
import sys
from unittest import mock

import pytest

from cms.models import Page

from django_cms_tools.fixtures.pages import CmsPageCreator

from publisher import constants
from publisher.models import PublisherStateModel
from publisher_tests.base import CmsBaseTestCase


class NewTestPageCreator(CmsPageCreator):
    def __init__(self, title, *args, parent_page=None, **kwargs):
        self.title = title
        self.parent_page = parent_page
        super().__init__(*args, **kwargs)

    def get_title(self, language_code, lang_name):
        return self.title

    def get_parent_page(self):
        return self.parent_page

    def publish(self, page):
        # don't publish the page
        return

    def fill_content(self, page, placeholder_slot):
        # don't create/add any placeholder/plugins
        return



@pytest.mark.django_db
class CmsPagePublisherWorkflowTests(CmsBaseTestCase):
    """
    Publisher workflow for CMS pages
    """
    def setUp(self):
        super(CmsPagePublisherWorkflowTests, self).setUp()

        public_pages = Page.objects.public()
        self.assertEqual(public_pages.count(), 5)

        page = public_pages[0]
        page.refresh_from_db()

        self.page4edit = page.get_draft_object()
        self.page4edit.refresh_from_db()

        self.page4edit_url = self.page4edit.get_absolute_url(language="en")

        self.page4edit_title = self.page4edit.get_title_obj(language="en")
        self.page4edit_title.refresh_from_db()

        # self.parent_page4edit = self.page4edit.parent.get_draft_object()
        # self.parent_page4edit_url = self.parent_page4edit.get_absolute_url(language="en")

    def test_setUp(self):
        self.assertEqual(self.page4edit_url, "/en/")
        self.assertEqual(self.page4edit.publisher_is_draft, True)
        self.assertEqual(self.page4edit.is_dirty(language="en"), False)

        self.assertEqual(str(self.page4edit_title), "Test page 1 in English (test-page-1-in-english, en)")

        # self.assertEqual(self.parent_page4edit_url, "/en/XXX/")
        # self.assertEqual(self.parent_page4edit.get_title(language="en"), "XXX")
        # self.assertEqual(self.parent_page4edit.publisher_is_draft, True)
        # self.assertEqual(self.parent_page4edit.is_dirty(language="en"), False)

    def test_reporter_edit_unchanged_page(self):
        self.login_reporter_user()

        response = self.client.get(
            "%s?edit" % self.page4edit_url,
            HTTP_ACCEPT_LANGUAGE="en"
        )
        # debug_response(response)

        # 'reporter' user can create un-/publish requests:

        self.assertResponse(response,
            must_contain=(
                "django-ya-model-publisher", "Test page 1 in English",

                "Logout reporter",
                "Double-click to edit",

                # <a href="/en/admin/publisher/publisherstatemodel/2/23/request_unpublish/"...>Request unpublishing</a>
                "/request_unpublish/", "Request unpublishing",
            ),
            must_not_contain=(
                # <a href="/en/admin/cms/page/670/en/publish/"...>Publish page changes</a>
                "/publish/", "Publish page changes",

                # <a href="/de/admin/publisher/publisherstatemodel/2/614/request_publish/"...>Request publishing</a>
                "/request_publish/", "Request publishing",

                "Error", "Traceback",
            ),
            status_code=200,
            template_name="cms/base.html",
            html=False,
        )

    def test_editor_edit_unchanged_page(self):
        self.login_editor_user()

        self.assertEqual(self.page4edit.is_dirty(language="en"), False)

        response = self.client.get(
            "%s?edit" % self.page4edit_url,
            HTTP_ACCEPT_LANGUAGE="en"
        )
        # debug_response(response)

        # 'editor' user can accept/reject un-/publish requests:

        self.assertResponse(response,
            must_contain=(
                "django-ya-model-publisher", "Test page 1 in English",

                "Logout editor",
                "Double-click to edit",
            ),
            must_not_contain=(
                # <a href="/en/admin/publisher/publisherstatemodel/2/23/request_unpublish/"...>Request unpublishing</a>
                "/request_unpublish/", "Request unpublishing",

                # <a href="/de/admin/publisher/publisherstatemodel/2/614/request_publish/"...>Request publishing</a>
                "/request_publish/", "Request publishing",

                "Error", "Traceback",
            ),
            status_code=200,
            template_name="cms/base.html",
            html=False,
        )

        # "disabled" publish button:
        self.assertResponse(response,
            must_contain=(
                (
                    '<a href="/en/admin/cms/page/1/en/publish/"'
                    ' class="cms-btn cms-btn-disabled cms-btn-action cms-btn-publish">'
                    'Publish page changes'
                    '</a>'
                ),
            ),
            html=True
        )

    def test_reporter_edit_dirty_page(self):
        self.login_reporter_user() # can create un-/publish requests

        self.page4edit_title.title = "A new page title"
        self.page4edit_title.save()

        self.assertEqual(self.page4edit.is_dirty(language="en"), True)

        response = self.client.get(
            "%s?edit" % self.page4edit_url,
            HTTP_ACCEPT_LANGUAGE="en"
        )
        # debug_response(response)

        # 'reporter' user can create un-/publish requests:

        self.assertResponse(response,
            must_contain=(
                "A new page title",

                "Logout reporter",
                "Double-click to edit",

                # <a href="/de/admin/publisher/publisherstatemodel/2/614/request_publish/"...>Request publishing</a>
                "/request_publish/", "Request publishing",

                # <a href="/en/admin/publisher/publisherstatemodel/2/23/request_unpublish/"...>Request unpublishing</a>
                "/request_unpublish/", "Request unpublishing",
            ),
            must_not_contain=(
                # <a href="/en/admin/cms/page/670/en/publish/"...>Publish page changes</a>
                "/publish/", "Publish page changes",

                "Error", "Traceback",
            ),
            status_code=200,
            template_name="cms/base.html",
            html=False,
        )

    def test_reporter_edit_pending_page(self):
        reporter = self.login_reporter_user() # can create un-/publish requests
        self.assertTrue(reporter.has_perm("cms.change_page"))

        self.page4edit_title.title = "A new page title"
        self.page4edit_title.save()

        self.assertEqual(self.page4edit.is_dirty(language="en"), True)

        state_instance = PublisherStateModel.objects.request_publishing(
            user = reporter,
            publisher_instance = self.page4edit
        )

        response = self.client.get(
            "%s?edit" % self.page4edit_url,
            HTTP_ACCEPT_LANGUAGE="en",
        )

        self.assertRedirects(
            response,
            expected_url="%s?edit_off" % self.page4edit_url,
            fetch_redirect_response=False
        )
        self.assertMessages(response, ["This page 'A new page title' has pending publish request."])

    def test_reporter_publish_request_view(self):
        reporter = self.login_reporter_user() # can create un-/publish requests
        self.assertTrue(reporter.has_perm("cms.change_page"))

        self.page4edit_title.title = "A new page title"
        self.page4edit_title.save()

        self.assertEqual(self.page4edit.is_dirty(language="en"), True)

        request_publish_url = PublisherStateModel.objects.admin_request_publish_url(self.page4edit)
        print(request_publish_url)
        self.assert_startswith(request_publish_url, "/en/admin/publisher/publisherstatemodel/")
        self.assert_endswith(request_publish_url, "/request_publish/")

        response = self.client.get(request_publish_url, HTTP_ACCEPT_LANGUAGE="en")
        # debug_response(response)

        self.assertResponse(response,
            must_contain=(
                "Publisher",
                "Publisher States",
                "Request Publishing",

                "Note:",
                "Publisher History",
                "No changes, yet.",
            ),
            must_not_contain=("Error", "Traceback"),
            status_code=200,
            template_name="publisher/publisher_requests.html",
            html=False,
        )

    def test_reporter_create_publish_request(self):

        self.assertEqual(PublisherStateModel.objects.all().count(), 0)

        reporter = self.login_reporter_user() # can create un-/publish requests
        self.assertTrue(reporter.has_perm("cms.change_page"))

        self.page4edit_title.title = "A new page title"
        self.page4edit_title.save()

        self.assertEqual(self.page4edit.is_dirty(language="en"), True)

        request_publish_url = PublisherStateModel.objects.admin_request_publish_url(self.page4edit)
        print(request_publish_url)
        self.assert_startswith(request_publish_url, "/en/admin/publisher/publisherstatemodel/")
        self.assert_endswith(request_publish_url, "/request_publish/")

        response = self.client.post(
            request_publish_url,
            data={
                "note": "Please publish this cms page changes.",
                "_ask_publish": "This value doesn't really matter.",
            },
            HTTP_ACCEPT_LANGUAGE="de"
        )
        # debug_response(response)

        self.assertMessages(response, ["publish request created."])

        self.assertRedirects(response,
            expected_url="/?edit_off", # <- FIXME: https://github.com/wearehoods/django-ya-model-publisher/issues/9
            status_code=302,
            fetch_redirect_response=False
        )

        self.assertEqual(PublisherStateModel.objects.all().count(), 1)

        state = PublisherStateModel.objects.all()[0]
        self.assertEqual(
            str(state),
            '"A new page title" publish request from: reporter (Please publish this cms page changes.) (open)'
        )
        self.assertEqual(state.publisher_instance.pk, self.page4edit.pk)

    def test_reporter_create_publish_request_on_new_page(self):

        self.assertEqual(PublisherStateModel.objects.all().count(), 0)

        reporter = self.login_reporter_user() # can create un-/publish requests
        self.assertTrue(reporter.has_perm("cms.change_page"))

        # parent page

        parent_page = Page.objects.public()[1]
        parent_page_url = parent_page.get_absolute_url(language="en")
        self.assertEqual(parent_page_url, "/en/test-page-2-in-english/")

        # new page 1

        new_page1, created = NewTestPageCreator(
            title="new page 1",
            parent_page=parent_page.get_draft_object()
        ).create()
        self.assertTrue(created)

        new_page1_url = new_page1.get_absolute_url(language="en")
        self.assertEqual(new_page1_url, "/en/test-page-2-in-english/new-page-1/")

        # new page 2

        new_page2, created = NewTestPageCreator(
            title="new page 2",
            parent_page=new_page1.get_draft_object()
        ).create()
        self.assertTrue(created)

        new_page2_url = new_page2.get_absolute_url(language="en")
        self.assertEqual(new_page2_url, "/en/test-page-2-in-english/new-page-1/new-page-2/")

        self.login_reporter_user()

        # Set CMS edit mode, otherwise we didn't see non published pages ;)
        session = self.client.session
        session['cms_edit'] = True
        session.save()

        request_publish_url = PublisherStateModel.objects.admin_request_publish_url(new_page2)
        print(request_publish_url)
        self.assert_startswith(request_publish_url, "/en/admin/publisher/publisherstatemodel/")
        self.assert_endswith(request_publish_url, "/request_publish/")

        response = self.client.post(
            request_publish_url,
            data={
                "note": "publish new page 2",
                "_ask_publish": "This value doesn't really matter.",
            },
            HTTP_ACCEPT_LANGUAGE="de"
        )
        # debug_response(response)

        self.assertMessages(response, ["publish request created."])

        # We have create a new cms page.
        # This page is not public visible.
        # A redirect to /en/test-new-emtpy-created-cms-page/?edit_off will raise a 404

        # TODO: redirect must be done to the first publish page
        # See: https://github.com/wearehoods/django-ya-model-publisher/issues/9
        # see also:
        # publisher.admin.PublisherStateModelAdmin#redirect_to_parent

        self.assertRedirects(response,
            expected_url="/?edit_off", # <- FIXME: https://github.com/wearehoods/django-ya-model-publisher/issues/9
            status_code=302,
            fetch_redirect_response=False
        )
        # self.assertRedirects(response,
        #     expected_url="http://testserver/en/test-page-2-in-english/?edit_off",
        #     status_code=302,
        #     fetch_redirect_response=True
        # )

        self.assertEqual(PublisherStateModel.objects.all().count(), 1)

        state = PublisherStateModel.objects.all()[0]
        self.assertEqual(
            str(state),
            '"new page 2" publish request from: reporter (publish new page 2) (open)'
        )
        self.assertEqual(state.publisher_instance.pk, new_page2.pk)

    def test_reporter_unpublish_request_view(self):
        reporter = self.login_reporter_user() # can create un-/publish requests
        self.assertTrue(reporter.has_perm("cms.change_page"))

        self.assertEqual(self.page4edit.is_dirty(language="en"), False)

        request_unpublish_url = PublisherStateModel.objects.admin_request_unpublish_url(self.page4edit)
        print(request_unpublish_url)
        self.assert_startswith(request_unpublish_url, "/en/admin/publisher/publisherstatemodel/")
        self.assert_endswith(request_unpublish_url, "/request_unpublish/")

        response = self.client.get(request_unpublish_url, HTTP_ACCEPT_LANGUAGE="en")
        # debug_response(response)

        self.assertResponse(response,
            must_contain=(
                "Publisher",
                "Publisher States",
                "Request Unpublishing",

                "Note:",
                "Publisher History",
                "No changes, yet.",
            ),
            must_not_contain=("Error", "Traceback"),
            status_code=200,
            template_name="publisher/publisher_requests.html",
            html=False,
        )

    def test_reporter_create_unpublish_request(self):

        self.assertEqual(PublisherStateModel.objects.all().count(), 0)

        reporter = self.login_reporter_user() # can create un-/publish requests
        self.assertTrue(reporter.has_perm("cms.change_page"))

        self.assertEqual(self.page4edit.is_dirty(language="en"), False)

        request_unpublish_url = PublisherStateModel.objects.admin_request_unpublish_url(self.page4edit)
        print(request_unpublish_url)
        self.assert_startswith(request_unpublish_url, "/en/admin/publisher/publisherstatemodel/")
        self.assert_endswith(request_unpublish_url, "/request_unpublish/")

        response = self.client.post(
            request_unpublish_url,
            data={
                "note": "Please unpublish this cms page.",
                "_ask_publish": "This value doesn't really matter.",
            },
            HTTP_ACCEPT_LANGUAGE="de"
        )
        # debug_response(response)

        self.assertRedirects(response,
            expected_url="/?edit_off", # <- FIXME: https://github.com/wearehoods/django-ya-model-publisher/issues/9
            status_code=302,
            fetch_redirect_response=False
        )

        self.assertEqual(PublisherStateModel.objects.all().count(), 1)

        state = PublisherStateModel.objects.all()[0]
        self.assertEqual(
            str(state),
            '"Test page 1 in English" unpublish request from: reporter (Please unpublish this cms page.) (open)'
        )
        self.assertEqual(state.publisher_instance.pk, self.page4edit.pk)

        self.assertMessages(response, ["unpublish request created."])


    #-------------------------------------------------------------------------


    def test_editor_reply_publish_request_view(self):
        self.page4edit_title.title = "A new page title"
        self.page4edit_title.save()

        self.assertEqual(self.page4edit.is_dirty(language="en"), True)

        reporter_user = self.UserModel.objects.get(username="reporter")
        state_instance = PublisherStateModel.objects.request_publishing(
            user = reporter_user,
            publisher_instance = self.page4edit
        )

        reply_url = state_instance.admin_reply_url()
        print(reply_url)
        self.assert_startswith(reply_url, "/en/admin/publisher/publisherstatemodel/")
        self.assert_endswith(reply_url, "/reply_request/")

        self.login_editor_user() # can accept/reject un-/publish requests

        response = self.client.get(reply_url, HTTP_ACCEPT_LANGUAGE="en")
        # debug_response(response)

        self.assertResponse(response,
            must_contain=(
                "Publisher",
                "Publisher States",
                "Accept/Reject Publish Request",
                "Note:",
                "&quot;A new page title&quot; publish request from: reporter (open)",
                "Publisher History",
            ),
            must_not_contain=(
                "No changes, yet.",
                "Error", "Traceback"
            ),
            status_code=200,
            template_name="publisher/publisher_requests.html",
            html=False,
        )

    def test_editor_accept_publish_request(self):
        self.page4edit_title.title = "A new page title"
        self.page4edit_title.save()

        self.assertEqual(self.page4edit.is_dirty(language="en"), True)

        reporter_user = self.UserModel.objects.get(username="reporter")
        state_instance = PublisherStateModel.objects.request_publishing(
            user = reporter_user,
            publisher_instance = self.page4edit
        )

        reply_url = state_instance.admin_reply_url()
        print(reply_url)
        self.assert_startswith(reply_url, "/en/admin/publisher/publisherstatemodel/")
        self.assert_endswith(reply_url, "/reply_request/")

        self.login_editor_user()

        def raise_error(*args, **kwargs):
            tb = sys.exc_info()[2]
            raise AssertionError().with_traceback(tb)

        # django/conf/urls/__init__.py:13 - handler400
        with mock.patch('django.views.defaults.bad_request', new=raise_error):
            response = self.client.post(
                reply_url,
                data={
                    "note": "OK, I publish this cms page, now.",
                    constants.POST_REPLY_ACCEPT_KEY: "This value doesn't really matter.",
                },
                HTTP_ACCEPT_LANGUAGE="de"
            )
            # debug_response(response)

        self.assertRedirects(response,
            expected_url="http://testserver/en/",
            status_code=302,
            fetch_redirect_response=False
        )

        self.assertEqual(PublisherStateModel.objects.all().count(), 1)

        state = PublisherStateModel.objects.all()[0]
        self.assertEqual(
            str(state),
            '"A new page title" publish accepted from: editor (OK, I publish this cms page, now.)'
        )
        self.assertEqual(state.publisher_instance.pk, self.page4edit.pk)

        self.page4edit = Page.objects.get(pk=self.page4edit.pk)
        self.assertEqual(self.page4edit.is_dirty(language="en"), False)

        self.assertMessages(response, [
            '"A new page title" publish accepted from: editor (OK, I publish this cms page, now.) has been accept.'
        ])

    def test_editor_reject_publish_request(self):
        self.page4edit_title.title = "A new page title"
        self.page4edit_title.save()

        self.assertEqual(self.page4edit.is_dirty(language="en"), True)

        reporter_user = self.UserModel.objects.get(username="reporter")
        state_instance = PublisherStateModel.objects.request_publishing(
            user = reporter_user,
            publisher_instance = self.page4edit
        )

        reply_url = state_instance.admin_reply_url()
        print(reply_url)
        self.assert_startswith(reply_url, "/en/admin/publisher/publisherstatemodel/")
        self.assert_endswith(reply_url, "/reply_request/")

        self.login_editor_user() # can accept/reject un-/publish requests

        def raise_error(*args, **kwargs):
            tb = sys.exc_info()[2]
            raise AssertionError().with_traceback(tb)

        # django/conf/urls/__init__.py:13 - handler400
        with mock.patch('django.views.defaults.bad_request', new=raise_error):
            response = self.client.post(
                reply_url,
                data={
                    "note": "No, I reject this request.",
                    constants.POST_REPLY_REJECT_KEY: "This value doesn't really matter.",
                },
                HTTP_ACCEPT_LANGUAGE="de"
            )
            # debug_response(response)

        self.assertRedirects(response,
            expected_url="http://testserver/en/",
            status_code=302,
            fetch_redirect_response=False
        )

        self.assertEqual(PublisherStateModel.objects.all().count(), 1)

        state = PublisherStateModel.objects.all()[0]
        self.assertEqual(
            str(state),
            '"A new page title" publish rejected from: editor (No, I reject this request.)'
        )
        self.assertEqual(state.publisher_instance.pk, self.page4edit.pk)

        self.page4edit = Page.objects.get(pk=self.page4edit.pk)
        self.assertEqual(self.page4edit.is_dirty(language="en"), True)

        self.assertMessages(response, [
            '"A new page title" publish rejected from: editor (No, I reject this request.) has been rejected.'
        ])

    def test_new_emtpy_created_cms_page(self):
        page, created = NewTestPageCreator(title="test_new_emtpy_created_cms_page").create()
        self.assertTrue(created)

        url = page.get_absolute_url(language="en")
        self.assertEqual(url, "/en/test-new-emtpy-created-cms-page/")

        pages = Page.objects.drafts()
        urls = [page.get_absolute_url(language="en") for page in pages]
        self.assertIn("/en/test-new-emtpy-created-cms-page/", urls)

        self.login_reporter_user()

        # Set CMS edit mode, otherwise we didn't see non published pages ;)
        session = self.client.session
        session['cms_edit'] = True
        session.save()

        response = self.client.get(url, HTTP_ACCEPT_LANGUAGE="en")
        self.assertResponse(response,
            must_contain=(
                "<title>test_new_emtpy_created_cms_page</title>",
                "Double-click to edit",

                # <a href="/de/admin/publisher/publisherstatemodel/2/614/request_publish/"...>Request publishing</a>
                "/request_publish/", "Request publishing",
            ),
            must_not_contain=("Error", "Traceback"),
            status_code=200,
            messages=[],
            template_name="cms/base.html", # Normal CMS page
            html=False,
        )
