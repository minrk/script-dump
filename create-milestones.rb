# create milestones on all the repos
require 'rubygems'
require 'Octokit'
require 'pry'

github = Octokit::Client.new(:netrc => true)

repos = [
  'ipython/ipywidgets',
  'ipython/ipykernel',
  'ipython/ipyparallel',
  'jupyter/jupyter_client',
  'ipython/traitlets',
  'ipython/ipyparallel',
  'jupyter/jupyter_core',
  'jupyter/jupyter_console',
  'jupyter/qtconsole',
  'jupyter/nbformat',
  'jupyter/nbconvert',
  'jupyter/notebook',
]

milestones = [
  'no action',
  'wishlist',
  '4.0',
  '4.1',
  '5.0',
]

repos.each do |repo|
  existing_milestones = github.list_milestones(repo).map { |ms| ms.title }
  existing_milestones += github.list_milestones(repo, :state => 'closed').map { |ms| ms.title }
  milestones.each do |ms|
    if not existing_milestones.include? ms
      puts "Creating #{repo}:#{ms}"
      github.create_milestone(repo, ms)
    else
      puts "#{repo}:#{ms} already exists"
    end
  end
end
  