��    v      �  �   |      �	  �   �	  �   �
  W  ^  g  �  h       �     �     �     �     �  8   �  N   !  $   p  R   �     �               <     Z     i     n  N   {     �     �     �     �       &   	     0  !   8     Z     t     �  #   �  
   �  7   �          )     >     N     V     ]     n     v     �  B   �  8   �  *   !     L     S     h     z     �     �     �     �     �  &   �  
   �      �  -   	     7     G     U      i  �   �            	   .     8     F  )   N     x     �  '   �  +   �     �          1  	   O  
   Y     d  /   t     �  8   �     �  %   �  '   #  9   K  5   �     �     �     �  !   �       #        4     8  &   A  E   h     �     �     �     �  .   �  6     @   U  '   �     �  	   �  (   �     �  $         4     U  �   ]  i      W  l   �   �!  �   R"  �  )#  �  &  5  )     O-     i-     p-     �-     �-  H   �-  J   .  6   P.  o   �.  !   �.     /  "   3/     V/     t/     �/     �/  e   �/      �/     0  	   !0     +0     G0  8   N0  	   �0  +   �0  $   �0  (   �0  %   1  *   11  
   \1  <   g1     �1     �1     �1     �1  	   �1     2  	   2     $2     >2  E   Y2  I   �2  <   �2     &3     /3     H3     ]3     d3     l3     q3     z3     �3  (   �3     �3  *   �3  3   4     54     I4     \4  *   {4  �   �4     J5     Q5     k5     w5     �5  /   �5     �5     �5  8   �5  ;   16  &   m6     �6  )   �6     �6     �6     �6  >   7     N7  H   Z7  !   �7  1   �7  5   �7  Z   -8  B   �8     �8     �8     �8  $   �8     9  1   49  
   f9     q9  &   }9  f   �9     :     !:     9:     Y:  =   a:  4   �:  :   �:  $   ;     4;     G;  /   S;     �;  '   �;  (   �;     �;  �   �;  y   �<     q   G   (   W              =   #       n   !   )              A   Q   ^   o          C          0   7      m   *   $   4       N   Y   Z       ]       U       <          T       8   R       
      L      H   i          b   -       J   6   @   h          "          j               t       9   /   O   s       `   X   	          d   V          3      P   1   S      p          M                 ,   D   &   2       5   F   :       r       '   .   K   a   >               f   c   E       e                 l   B      g       ;      k         \   _   [   ?             I      u          v   +   %                            Gateway : {gateway}
                        Remote status : {status}
                        Message : {message}
                                         Path: {authenticator_dir}
                    ID: {keystore_uid}
                    User: {keystore_owner}
                    Password hint: {keystore_passphrase_hint}
                         On this page, you can initialize an authenticator inside an empty folder; this authenticator actually consists in metadata files as well as a set of asymmetric keypairs.

        To proceed, you have to input your user name or pseudo, a long passphrase (e.g. consisting of 4 different words), and a public hint to help your remember your passphrase later.

        You should keep your passphrase somewhere safe (in a digital password manager, on a paper in a vault...), because if you forget any of its aspects (upper/lower case, accents, spaces...), there is no way to recover it.
                 On this page, you can initialize an authenticator inside an empty folder; this authenticator actually consists in metadata files as well as a set of asymmetric keypairs.
        
        To proceed, you have to input your user name or pseudo, a long passphrase (e.g. consisting of 4 different words), and a public hint to help your remember your passphrase later.
        
        You should keep your passphrase somewhere safe (in a digital password manager, on a paper in a vault...), because if you forget any of its aspects (upper/lower case, accents, spaces...), there is no way to recover it.
                 On this page, you can manage your authenticators, which are actually digital keychains identified by unique IDs.
        
        These keychains contain both public keys, which can be freely shared, and their corresponding private keys, protected by passphrases, which must be kept hidden.
        
        Authenticators can be stored in your user profile or in a custom folder, especially at the root of removable devices.
        
        You can initialize new authenticators from scratch, import/export them from/to ZIP archives, or check their integrity by providing their passphrases.
        
        Note that if you destroy an authenticator and all its exported ZIP archives, the WitnessAngel recordings which used it as a trusted third party might not be decryptable anymore (unless they used a shared secret with other trusted third parties).
          Passphrase: {passphrase} <empty> Abnormal error caught: %s Accepted passphrase Add a passphrase All authentication data from folder %s has been removed. An inconsistency has been detected between the local and remote authenticator. Authenticator archive exported to %s Authenticator archive unpacked from %s, its integrity has not been checked though. Authenticator creation page Authenticator initialized Authenticator management page Authenticator not initialized Authenticator: Back Back to home Beware, this might make encrypted data using these keys impossible to decrypt. Camera url: {camera_url} Cancel Check Checkup result: %s Close Configuration errors prevent recording Confirm Container decryption confirmation Container decryption page Container deletion confirmation Container storage is invalid Container storage: {cryptainer_dir} Containers Containers are kept for {max_cryptainer_age_day} day(s) Control Recorder Create Authenticator Custom location Decrypt Delete Deletion is over Destroy Destroy authenticator Drive: {drive} ({label}) Each container stores {video_recording_duration_mn} mn(s) of video Enter the passphrase to decrypt the selected containers: Error calling method, check the server url Export Export authenticator Export successful Failure Found Help Import Import from USB Import successful Initialization successfully completed. Initialize Invalid authenticator data in %s Invalid container storage: "{cryptainer_dir}" Key Guardian %s Key Guardians Key Guardians used: Keypairs successfully tested: %s Keypairs tested: {keypair_count}
Missing private keys: {missing_private_keys}
Wrong passphrase for keys:  {undecodable_private_keys} Language Manage Authenticators NOT Found NOT PUBLISHED NOT Set No connected authentication devices found No containers found No containers selected No imported authentication device found No initialized authentication devices found No valid location selected N° {index}: {cryptainer_name} Operation failed, check logs. PUBLISHED Passphrase Passphrase hint Passphrase must be at least %s characters long. Path: %s Please enter a username, passphrase and passphrase hint. Please select a folder Please select an authenticator folder Please select an authenticator location Please select the key guardians used to secure recordings Please wait, initialization might take a few minutes. Publish Publish authenticator Refresh Refreshed imported authenticators Sanity check Selected folder is invalid
Path: %s Set Settings Size: {size}, Filesystem: {filesystem} Some configuration changes might only apply at next recording restart Start Recording Stop Recording Stored inside system disk Success Test integrity and passphrase of authenticator The exported archive should be kept in a secure place. The local authenticator does not exist on the remote repository. The remote authenticator is up to date. User Profile User name User {keystore_owner}, id {keystore_uid} Validation error View and manage encrypted containers Wrong camera url: "{camera_url}" no name {imported_keystore_count} authenticators properly imported, {already_existing_keystore_count} already existing, {corrupted_keystore_count} skipped because corrupted {keyguardian_count} key guardian(s) configured, {keyguardian_threshold} of which necessary for decryption Project-Id-Version: WitnessAngelGuilib
Report-Msgid-Bugs-To: 
PO-Revision-Date: 2022-02-01 12:26+0200
Last-Translator: Pascal <pythoniks@gmail.com>
Language-Team: Nothing
Language: fr
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
Plural-Forms: nplurals=2; plural=(n > 1);
X-Generator: Virtaal 0.7.1
                         Passerelle : {gateway}
                        Statut distant : {status}
                        Message : {message}
                     Chemin : {authenticator_dir}
                    ID : {keystore_uid}
                    Utilisateur : {keystore_owner}
                    Indice de phrase secrète : {keystore_passphrase_hint}         Sur cette page, vous pouvez initialiser un authentifieur dans un dossier vide ; cet authentifieur consiste en réalité en des fichiers de métadonnées, ainsi qu'en un ensemble de paires de clés asymétriques.

        Pour procéder, vous devez entrer votre nom d'utilisateur ou pseudo, une longue phrase secrète (par exemple, composée de 4 mots différents), et un indice public pour vous aider à vous souvenir de votre phrase secrète plus tard.

        Vous devez conserver votre phrase secrète en lieu sûr (dans un gestionnaire de mots de passe numérique, sur un papier dans un coffre-fort...), car si vous oubliez l'un de ses aspects (majuscules/minuscules, accents, espaces...), il n'y a aucun moyen de la récupérer.
                 Sur cette page, vous pouvez initialiser un authentifieur dans un dossier vide ; cet authentifieur consiste en réalité en des fichiers de métadonnées, ainsi qu'en un ensemble de paires de clés asymétriques.
        
        Pour procéder, vous devez entrer votre nom d'utilisateur ou pseudo, une longue phrase secrète (par exemple, composée de 4 mots différents), et un indice public pour vous aider à vous souvenir de votre phrase secrète plus tard.
        
        Vous devez conserver votre phrase secrète en lieu sûr (dans un gestionnaire de mots de passe numérique, sur un papier dans un coffre-fort...), car si vous oubliez l'un de ses aspects (majuscules/minuscules, accents, espaces...), il n'y a aucun moyen de la récupérer.
                 Sur cette page, vous pouvez gérer vos authentifieurs, qui sont en fait des trousseaux de clés numériques identifiés par des ID uniques.
        
        Ces trousseaux contiennent à la fois des clés publiques, qui peuvent être partagées librement, et les clés privées correspondantes, protégées par des phrases secrètes, qui doivent rester cachées.
        
        Les authentifieurs peuvent être stockés dans votre profil utilisateur ou dans un dossier personnalisé, notamment à la racine des périphériques amovibles.
        
        Vous pouvez initialiser de nouveaux authentifieurs à partir de zéro, les importer/exporter depuis/vers des archives ZIP, ou vérifier leur intégrité en fournissant leurs phrases secrètes.
        
        Notez que si vous détruisez un authentifieurs et toutes ses archives ZIP exportées, les enregistrements WitnessAngel qui l'utilisaient en tant que tiers de confiance risquent de ne plus pouvoir être déchiffrés (à moins qu'ils n'aient utilisé un secret partagé avec d'autres tiers de confiance).  Passphrase: {passphrase} <vide> Erreur anormale détectée : %s Phrase secrète Ajouter une phrase secrète Toutes les données d'authentifieur du dossier %s ont été supprimées. Une incohérence a été détectée entre l'authentifieur local et distant L'archive de l'authentifieur a été exportée vers %s L'archive d'authentifieur a été décompressée depuis %s, son intégrité n'a cependant pas été vérifiée. Page de création d'authentifieur Authentifieur initialisé Page de gestion des authentifieurs Authentifieur non initialisé Authentifieur : Retour Retour Attention, cela peut rendre impossible le déchiffrement des données chiffrées utilisant ces clés. Url de la caméra : {camera_url} Annuler Vérifier Résultat du contrôle : %s Fermer Des erreurs de configuration empêchent l'enregistrement Confirmer Confirmation de déchiffrement de conteneur Page de déchiffrement de conteneurs Confirmation de suppression de conteneur Le dépôt de conteneurs est invalide Stockage des conteneurs : {cryptainer_dir} Conteneurs Les conteneurs sont gardés {max_cryptainer_age_day} jour(s) Contrôler Enregistreur Créer un Authentifieur Emplacement personnalisé Déchiffrer Supprimer Destruction terminée Détruire Détruire l'authentifieur Disque : {drive} ({label}) Chaque conteneur stocke {video_recording_duration_mn} mn(s) de vidéo Entrez la phrase secrète pour déchiffrer les conteneurs sélectionnés. Erreur à l'appel de la méthode, vérifier l'url du serveur Exporter Exporter l'authentifieur Exportation réussie Échec Trouvé Aide Importer Import depuis USB Importation réussie Initialisation complétée avec succès. Initialiser Données d'authentifieur invalides dans %s Stockage des conteneurs invalide : {cryptainer_dir} Gardiens de Clé %s Gardiens des Clés Gardiens des Clés utilisés : Paires de clés testées avec succès : %s Paires de clés testées : {keypair_count}
Clés privées manquantes : {missing_private_keys}
Mauvaise phrase secrète pour les clés :  {undecodable_private_keys} Langue Gérer les Authentifieurs NON Trouvé NON PUBLIÉ NON Renseigné Aucun périphérique d'authentification trouvé Aucun conteneur trouvé Aucun conteneur sélectionné Aucun périphérique d'authentification importé trouvé Aucun périphérique d'authentification initialisé trouvé Aucun emplacement valide sélectionné N° {index}: {cryptainer_name} Opération échouée, vérifiez les logs. PUBLIÉ Phrase secrète Indice de phrase secrète La phrase secrète doit faire au moins %s caractères de long. Chemin : %s Veuillez entrer un nom d'utilisateur, une phrase secrète et son indice. Veuillez sélectionner un dossier Veuillez sélectionner un dossier d'authentifieur Veuillez sélectionner un emplacement d'authentifieur Veuillez sélectionner les gardiens de clés utilisés pour sécuriser les enregistrements Veuillez attendre, l'initialisation peut prendre quelques minutes. Publier Publier l'authentifieur Rafraîchir Authentifieurs importés rafraîchis Contrôle d'intégrité Le dossier sélectionné est invalide
Chemin : %s Renseigné Paramètres Taille : {size}, Format : {filesystem} Certains changements de configuration pourraient ne s'appliquer qu'au redémarrage de l'enregistrement Lancer Enregistrement Arrêter Enregistrement Stocké dans le disque système Succès Tester l'intégrité et la phrase secrète de l'authentifieur L'archive exportée doit être gardée en lieu sûr. L'authentifieur local n'existe pas dans le dépôt distant L'authentifieur distant est à jour. Profil Utilisateur Utilisateur Utilisateur {keystore_owner}, id {keystore_uid} Erreur de validation Voir et gérer les conteneurs chiffrés Mauvaise url de caméra : "{camera_url}" sans nom {imported_keystore_count} authentifieurs importé(s) avec succès, {already_existing_keystore_count} déjà existant(s), {corrupted_keystore_count} ignoré(s) car corrompu(s) {keyguardian_count} gardien(s) de clés configuré(s), dont {keyguardian_threshold} nécessaire(s) pour le déchiffrement 