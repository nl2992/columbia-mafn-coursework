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
# Remove the obsolete shell entry point left by pre-native Desktop installs.
/bin/rm -f "${desktop_app}/Contents/MacOS/launch"
print -r -- "${repo_root}" > "${desktop_app}/Contents/Resources/repository-path.txt"
/usr/bin/codesign --force --deep --sign - "${desktop_app}"
/usr/bin/touch "${desktop_app}"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "${desktop_app}"
/usr/bin/open -n "${desktop_app}"
