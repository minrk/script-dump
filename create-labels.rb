require 'rubygems'
require 'Octokit'

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

labels = [
  'sprint-friendly',
]

repos.each do |repo|
  existing_labels = github.labels(repo).map { |label| label.name }
  labels.each do |label|
    if not existing_labels.include? label
      puts "Creating #{repo}:#{label}"
      github.add_label(repo, label, "02d7e1")
    else
      puts "#{repo}:#{label} already exists"
    end
  end
end
  