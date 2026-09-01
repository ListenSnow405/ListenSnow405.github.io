# frozen_string_literal: true

source "https://rubygems.org"

# Match the dependency set used by GitHub Pages.
gem "github-pages", "~> 232", group: :jekyll_plugins

# Windows does not ship the IANA time zone database used by Jekyll.
platforms :mingw, :x64_mingw, :mswin, :jruby do
  gem "tzinfo", ">= 1", "< 3"
  gem "tzinfo-data"
end
