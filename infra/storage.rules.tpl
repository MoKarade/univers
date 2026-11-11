rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /{allPaths=**} {
      allow read: if request.auth != null
                  && request.auth.token.email_verified == true
                  && request.auth.token.email == '__AUTHORIZED_EMAIL__';
      allow write: if false;
    }
  }
}
