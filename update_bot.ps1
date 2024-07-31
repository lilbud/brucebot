# quick way to enable/disable testing
$message = Read-Host("commit message:")

while ($message -eq "") {
    $message = Read-Host("commit message:")
}

git add .
git commit -m $message
git push origin main
git push heroku main
