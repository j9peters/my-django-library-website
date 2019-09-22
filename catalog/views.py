from .forms import RenewBookForm
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Book, Author, BookInstance, Genre

import datetime

# Create your views here.


class AuthorListView(generic.ListView):
    model = Author
    template_name = "authors/author_list.html"
    paginate_by = 10


class AuthorDetailView(generic.DetailView):
    model = Author
    template_name = "authors/author_detail.html"


class BookListView(generic.ListView):
    model = Book
    context_object_name = "my_book_list"  # your own name for the list as a template variable
    template_name = "books/book_list.html"  # Specify your own template name / location
    paginate_by = 10


class BookDetailView(generic.DetailView):
    model = Book
    template_name = "books/book_detail.html"


class LoanedBooksByUserListView(LoginRequiredMixin, generic.ListView):
    """Generic class-based view listing books on loan to current user."""
    model = BookInstance
    template_name = "users/bookinstance_list_borrowed_user.html"
    paginate_by = 10

    def get_queryset(self):
        return BookInstance.objects.filter(borrower=self.request.user).filter(status__exact='o')


class AllBorrowedBooksListView(PermissionRequiredMixin, generic.ListView):
    model = BookInstance
    template_name = "books/all_borrowed_books.html"
    paginate_by = 10
    permission_required = 'catalog.can_view_all_borrowed_books'

    def get_queryset(self):
        return BookInstance.objects.filter(status__exact='o')


class AuthorCreate(PermissionRequiredMixin, CreateView):
    model = Author
    fields = '__all__'
    initial = {'date_of_death': '05/01/2018'}
    permission_required = 'catalog.can_view_all_borrowed_books'


class AuthorUpdate(PermissionRequiredMixin, UpdateView):
    model = Author
    fields = ['first_name', 'last_name', 'date_of_birth', 'date_of_death']
    permission_required = 'catalog.can_view_all_borrowed_books'


class AuthorDelete(PermissionRequiredMixin, DeleteView):
    model = Author
    success_url = reverse_lazy('authors')
    permission_required = 'catalog.can_view_all_borrowed_books'


class BookCreate(PermissionRequiredMixin, CreateView):
    model = Book
    fields = '__all__'
    permission_required = 'catalog.can_view_all_borrowed_books'


class BookUpdate(PermissionRequiredMixin, UpdateView):
    model = Book
    fields = '__all__'
    permission_required = 'catalog.can_view_all_borrowed_books'


class BookDelete(PermissionRequiredMixin, DeleteView):
    model = Book
    success_url = reverse_lazy('books')
    permission_required = 'catalog.can_view_all_borrowed_books'


def index(request):
    """View function for home page of site."""

    num_fantasy_genres = Genre.objects.filter(name__icontains="fantasy").count()
    num_book_titles_containing_code = Book.objects.filter(title__icontains="code").count()

    # Generate counts of some of the main objects
    num_books = Book.objects.all().count()
    num_instances = BookInstance.objects.all().count()

    # Available books (status = "a")
    num_instances_available = BookInstance.objects.filter(status__exact="a").count()

    # The "all()" is implied by default
    num_authors = Author.objects.count()

    # Number of visits to this view, as counted in the session variable.
    num_visits = request.session.get('num_visits', 1)  # Get the value of the num_visits session key, setting the value to 1 if it has not previously been set.
    request.session['num_visits'] = num_visits + 1

    context = {
        "num_books": num_books,
        "num_instances": num_instances,
        "num_instances_available": num_instances_available,
        "num_authors": num_authors,
        "num_fantasy_genres": num_fantasy_genres,
        "num_book_titles_containing_code": num_book_titles_containing_code,
        "num_visits": num_visits,
    }

    # Render the HTML template index.html with the data in the context variable
    return render(request, "index.html", context=context)


@permission_required("catalog.can_mark_returned")
def renew_book_librarian(request, pk):
    """View function for a librarian to renew a specific BookInstance."""
    book_instance = get_object_or_404(BookInstance, pk=pk)

    # If this is a POST request then process the Form data
    if request.method == 'POST':

        # Create a form instance and populate it with data from the request (binding)
        form = RenewBookForm(request.POST)

        # Check if the form is valid
        if form.is_valid():
            # process the data in form.cleaned_data as required
            book_instance.due_back = form.cleaned_data["renewal_date"]
            book_instance.save()

            # redirect to a new URL
            return HttpResponseRedirect(reverse("all-borrowed-books"))

    # if this is a GET (or any other method) create the default form
    else:
        proposed_renewal_date = datetime.date.today() + datetime.timedelta(weeks=3)
        form = RenewBookForm(initial={"renewal_date": proposed_renewal_date})

    context = {
        "form": form,
        "book_instance": book_instance,
    }

    return render(request, "books/book_renew_librarian.html", context)