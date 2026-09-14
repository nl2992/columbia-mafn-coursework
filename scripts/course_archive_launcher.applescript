-- Source for Course Archive.app/Contents/Resources/Scripts/main.scpt.
-- Rebuild with: osacompile -o /private/tmp/CourseArchive.app scripts/course_archive_launcher.applescript
on run
  set appPath to POSIX path of (path to me)
  set helperPath to appPath & "Contents/MacOS/launch-helper"
  do shell script "/usr/bin/nohup " & quoted form of helperPath & " >/dev/null 2>&1 &"
end run
