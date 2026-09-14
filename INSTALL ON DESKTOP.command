#!/bin/zsh
set -eu

repo_root="${0:A:h}"
source_app="${repo_root}/Course Archive.app"
desktop_app="${HOME}/Desktop/Course Archive.app"

if [[ ! -d "${source_app}" ]]; then
  print -u2 "Course Archive.app is missing from ${repo_root}"
  exit 1
fi

/usr/bin/ditto "${source_app}" "${desktop_app}"
print -r -- "${repo_root}" > "${desktop_app}/Contents/Resources/repository-path.txt"
/usr/bin/touch "${desktop_app}"
/usr/bin/open "${desktop_app}"
