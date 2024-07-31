# quick way to enable/disable testing
$message = Read-Host("commit message:")

while ($message -eq "") {
    $message = Read-Host("commit message:")
}

git add .
git commit -am $message
git push github main
git push heroku main