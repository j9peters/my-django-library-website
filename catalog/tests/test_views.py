from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Author, Book, BookInstance, Genre, Language

import datetime
import uuid


class AuthorListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # create 13 authors for pagination tests
        number_of_authors = 13

        for author_id in range(1, number_of_authors + 1):
            Author.objects.create(
                first_name=f'John {author_id}',
                last_name=f'Doe {author_id}'
            )

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/catalog/authors/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(reverse('authors'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('authors'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authors/author_list.html')

    def test_pagination_is_ten(self):
        response = self.client.get(reverse('authors'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('is_paginated' in response.context)
        self.assertTrue(response.context['is_paginated'] == True)
        self.assertTrue(len(response.context['author_list']) == 10)

    def test_lists_all_authors(self):
        # get second page and confirm it has (exactly) remaining 3 items
        response = self.client.get(reverse('authors') + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('is_paginated' in response.context)
        self.assertTrue(response.context['is_paginated'] == True)
        self.assertTrue(len(response.context['author_list']) == 3)


class LoanedBookInstancesByUserListViewTest(TestCase):
    def setUp(self):
        test_user1 = User.objects.create_user(username='testuser1', password='drowssap1')
        test_user2 = User.objects.create_user(username='testuser2', password='drowssap2')

        test_user1.save()
        test_user2.save()

        test_author = Author.objects.create(first_name='John', last_name='Smith')
        test_genre = Genre.objects.create(name='Fantasy')
        test_language = Language.objects.create(name='English')
        test_book = Book.objects.create(
            title='Book Title',
            summary='My book summary',
            isbn='ABCDEFG',
            author=test_author,
            language=test_language
        )

        genre_objects_for_book = Genre.objects.all()
        test_book.genre.set(genre_objects_for_book)  # direct assignment of many-to-many types not allowed
        test_book.save()

        # create 30 BookInstance objects
        number_of_book_copies = 30
        for book_copy in range(number_of_book_copies):
            return_date = timezone.localtime() + datetime.timedelta(days=book_copy % 5)
            the_borrower = test_user1 if book_copy % 2 else test_user2
            status = 'm'
            BookInstance.objects.create(
                book=test_book,
                imprint='Unlikely Imprint, 2016',
                due_back=return_date,
                borrower=the_borrower,
                status=status
            )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('my-borrowed'))
        self.assertRedirects(response, '/accounts/login/?next=/catalog/mybooks/')

    def test_logged_in_uses_correct_template(self):
        self.client.login(username='testuser1', password='drowssap1')
        response = self.client.get(reverse('my-borrowed'))
        self.assertEqual(str(response.context['user']), 'testuser1')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/bookinstance_list_borrowed_user.html')

    def test_only_borrowed_books_in_list(self):
        self.client.login(username='testuser1', password='drowssap1')
        response = self.client.get(reverse('my-borrowed'))
        self.assertEqual(str(response.context['user']), 'testuser1')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('bookinstance_list' in response.context)
        self.assertEqual(len(response.context['bookinstance_list']), 0)
        books = BookInstance.objects.all()

        for book in books:
            book.status = 'o'
            book.save()

        response = self.client.get(reverse('my-borrowed'))
        self.assertEqual(str(response.context['user']), 'testuser1')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('bookinstance_list' in response.context)

        for bookitem in response.context['bookinstance_list']:
            self.assertEqual(response.context['user'], bookitem.borrower)
            self.assertEqual('o', bookitem.status)

    def test_pages_ordered_by_due_date(self):

        for book in BookInstance.objects.all():
            book.status = 'o'
            book.save()

        self.client.login(username='testuser1', password='drowssap1')
        response = self.client.get(reverse('my-borrowed'))
        self.assertEqual(str(response.context['user']), 'testuser1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['bookinstance_list']), 10)
        last_date = 0

        for book in response.context['bookinstance_list']:
            if last_date == 0:
                last_date = book.due_back
            else:
                self.assertTrue(last_date <= book.due_back)
                last_date = book.due_back


class RenewBookInstancesViewTest(TestCase):
    def setUp(self):
        test_user1 = User.objects.create_user(username='testuser1', password='drowssap1')
        test_user2 = User.objects.create_user(username='testuser2', password='drowssap2')
        test_user1.save()
        test_user2.save()

        permission = Permission.objects.get(name='Set book as returned')
        view_all_borrowed_books_permission = Permission.objects.get(name='View all borrowed books')
        test_user2.user_permissions.add(permission)
        test_user2.user_permissions.add(view_all_borrowed_books_permission)
        test_user2.save()

        test_author = Author.objects.create(first_name='John', last_name='Smith')
        test_genre = Genre.objects.create(name='Fantasy')
        test_language = Language.objects.create(name='English')
        test_book = Book.objects.create(
            title='Book Title',
            summary='Summary',
            isbn='ABCDEFG',
            author=test_author,
            language=test_language
        )

        genre_objects_for_book = Genre.objects.all()
        test_book.genre.set(genre_objects_for_book)  # direct assignment of many-to-many types not allowed
        test_book.save()

        # create a BookInstance object for test_user1
        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance1 = BookInstance.objects.create(
            book=test_book,
            imprint='Imprint',
            due_back=return_date,
            borrower=test_user1,
            status='o'
        )

        # create a BookInstance object for test_user2
        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance2 = BookInstance.objects.create(
            book=test_book,
            imprint='Imprint',
            due_back=return_date,
            borrower=test_user2,
            status='o'
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        # manually check redirect (can't use assertRedirect because the redirect URL is unpredictable
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_redirect_if_logged_in_but_not_correct_permission(self):
        self.client.login(username='testuser1', password='drowssap1')
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_logged_in_with_permission_borrowed_book(self):
        self.client.login(username='testuser2', password='drowssap2')
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance2.pk}))
        self.assertEqual(response.status_code, 200)

    def test_logged_in_with_permission_another_users_borrowed_book(self):
        self.client.login(username='testuser2', password='drowssap2')
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        self.assertEqual(response.status_code, 200)

    def test_HTTP404_for_invalid_book_if_logged_in(self):
        test_uid = uuid.uuid4()
        self.client.login(username='testuser2', password='drowssap2')
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': test_uid}))
        self.assertEqual(response.status_code, 404)

    def test_uses_correct_template(self):
        self.client.login(username='testuser2', password='drowssap2')
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/book_renew_librarian.html')

    def test_form_renewal_date_initially_has_date_three_weeks_in_future(self):
        self.client.login(username='testuser2', password='drowssap2')
        response = self.client.get(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))
        self.assertEqual(response.status_code, 200)
        date_3_weeks_in_future = datetime.date.today() + datetime.timedelta(weeks=3)
        self.assertEqual(response.context['form'].initial['renewal_date'], date_3_weeks_in_future)

    def test_redirects_to_all_borrowed_book_list_on_success(self):
        self.client.login(username='testuser2', password='drowssap2')
        valid_date_in_future = datetime.date.today() + datetime.timedelta(weeks=2)
        response = self.client.post(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}), {'renewal_date': valid_date_in_future})
        self.assertRedirects(response, reverse('all-borrowed-books'))

    def test_form_invalid_renewal_date_past(self):
        self.client.login(username='testuser2', password='drowssap2')
        date_in_past = datetime.date.today() - datetime.timedelta(weeks=1)
        response = self.client.post(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}), {'renewal_date': date_in_past})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'renewal_date', 'Invalid date - renewal in past')

    def test_form_invalid_renewal_date_future(self):
        self.client.login(username='testuser2', password='drowssap2')
        invalid_date_in_future = datetime.date.today() + datetime.timedelta(weeks=5)
        response = self.client.post(reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}), {'renewal_date': invalid_date_in_future})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'renewal_date', 'Invalid date - renewal more than 4 weeks ahead')


class AuthorCreateViewTest(TestCase):
    def test_not_logged_in(self):
        # attempt to navigate to Author creation page as an anonymous (i.e. not logged in) visitor
        response = self.client.get(reverse('author_create'))
        # ensure visitor is redirected to login page
        self.assertEquals(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_logged_in_but_no_permission(self):
        # create user *without* required permission
        User.objects.create_user(username='userwithoutpermission', password='cantaccesspage')
        # log in using unauthorized user
        self.client.login(username='userwithoutpermission', password='cantaccesspage')
        # navigate to Author creation page
        response = self.client.get(reverse('author_create'))
        # ensure unauthorized user is denied access to the page / response's status code is 403 Forbidden
        self.assertEquals(response.status_code, 403)

    def test_logged_in_with_permission(self):
        # create user with required permission
        user = User.objects.create_user(username='thisisauser', password='drowssap')
        permission = Permission.objects.get(name='View all borrowed books')
        user.user_permissions.add(permission)

        # log in using authorized user
        self.client.login(username='thisisauser', password='drowssap')
        # navigate to Author creation page
        response = self.client.get(reverse('author_create'))

        # ensure page is accessed successfully
        self.assertEquals(response.status_code, 200)

        # ensure form displays initial data for date of death
        self.assertEquals(list(response.context['form'].initial.keys()), ['date_of_death'])
        # ensure initial data is correct
        self.assertEquals(response.context['form'].initial['date_of_death'], '05/01/2018')

        # ensure form displays all of the Author model fields
        form_meta = response.context['form'].Meta
        self.assertEquals(form_meta.model, Author)
        self.assertEquals(form_meta.fields, '__all__')
        self.assertEquals(hasattr(form_meta, 'exclude'), False)

        # Author table currently has no records
        authors = Author.objects.all()
        self.assertEquals(len(authors), 0)

        # fill out form with acceptable values, i.e. add new Author to database
        response = self.client.post(reverse('author_create'), data={'first_name': 'Winnifred', 'last_name': 'Xerxes', 'date_of_birth': '01/01/2001'}, follow=True)

        # newly-created Author has been added to database
        authors = Author.objects.all()
        self.assertEquals(len(authors), 1)  # Author table contains 1 record
        new_author = authors[0]
        self.assertEquals(str(new_author), 'Xerxes, Winnifred')  # Author table contains the newly-created Author

        # ensure redirects to new Author's detail page on success
        self.assertRedirects(response, reverse('author-detail', kwargs={'pk': new_author.pk}))

        # ensure correct template is used
        self.assertTemplateUsed(response, 'authors/author_detail.html')
