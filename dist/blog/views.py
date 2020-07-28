from django.conf import settings
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count

from taggit.models import Tag

from . import forms
from . import models

'''
class PostListView(ListView):
	queryset = models.Post.published.all()
	context_object_name = 'posts'
	paginate_by = 4
	template_name = 'blog/post/list.html'
'''

def post_list(request, tag_slug=None):
	post_objects = models.Post.published.all()

	tag = None
	if tag_slug:
		tag = get_object_or_404(Tag, slug=tag_slug)
		post_objects = post_objects.filter(tags__in=[tag])

	paginator = Paginator(post_objects, 3) #3 post per page
	page = request.GET.get('page')

	try:
		posts = paginator.page(page)
	except PageNotAnInteger:
		posts = paginator.page(1)
	except EmptyPage:
		posts = paginator.page(paginator.num_pages)

	args = {'posts': posts, 'page': page, 'tag': tag}
	return render(request, 'blog/post/list.html', args)


def post_details(request, year, month, day, post):
	post = get_object_or_404(
		models.Post, slug=post, status='published', 
		publish__year=year, publish__month=month, publish__day=day)
	comments = post.comments.filter(active=True)
	new_comment = None
	if request.method == 'POST':
		comment_form = forms.CommentForm(data=request.POST)
		if comment_form.is_valid():
			new_comment = comment_form.save(commit=False)
			new_comment.post = post
			new_comment.save()
	else:
		comment_form = forms.CommentForm()
	
	post_tags_ids = post.tags.values_list('id', flat=True)
	simmilar_posts = models.Post.published.filter(tags__in=post_tags_ids)\
		.exclude(id=post.id)
	simmilar_posts = simmilar_posts.annotate(same_tags=Count('tags'))\
		.order_by('-same_tags', '-publish')[:4]

	args = {
		'post': post,
		'comments': comments,
		'new_comment': new_comment,
		'comment_form': comment_form,
		'simmilar_posts': simmilar_posts
	}
	return render(request, 'blog/post/details.html', args)


def post_share(request, post_id):
	post = get_object_or_404(models.Post, id=post_id, status='published')
	sent = False
	if request.method == 'POST':
		form = forms.EmailPostForm(request.POST)
		if form.is_valid():
			cd = form.cleaned_data
			post_url = request.build_absolute_uri(post.get_absolute_url())
			subject = '{} ({}) recommends you reading "{}"'.format(
				cd["name"], cd["email"], post.title)
			message = 'Read "{}" at {}\n\n{}\'s comments: {}'.format(
				post.title, post_url, cd["name"], cd["comments"])
			send_mail(subject, message, settings.EMAIL_HOST_USER, [cd["to"]])
			sent = True
	else:
		form = forms.EmailPostForm()
	
	args = {'post': post, 'form': form, 'sent': sent}
	return render(request, 'blog/post/share.html', args)