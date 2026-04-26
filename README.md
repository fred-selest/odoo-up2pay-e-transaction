# Payment Up2pay - Module Odoo

Module de paiement pour Odoo permettant d'intégrer la passerelle de paiement **Up2pay E-Transactions**.

## 📋 Description

Ce module permet de traiter les paiements via la passerelle de paiement Up2pay E-Transactions. Il fournit une intégration complète avec le système de paiement d'Odoo, incluant :

- **Paiement par redirection** vers la plateforme Up2pay
- **Authentification HMAC-SHA512** pour sécuriser les transactions
- **Support IPN** (Instant Payment Notification) pour la confirmation des paiements
- **Gestion des environnements** test et production

## 🚀 Fonctionnalités

- Intégration transparente avec le module `payment` d'Odoo
- Configuration simplifiée des identifiants marchand
- Signature cryptographique HMAC-SHA512 selon les spécifications Up2pay
- Gestion des retours de paiement (succès, échec, annulation)
- Support multi-devises (EUR, USD, GBP, CHF, CAD)
- Vérification automatique des signatures pour les notifications IPN

## 📦 Installation

### Prérequis

- Odoo 19.0 ou version compatible
- Module `payment` installé
- Compte marchand Up2pay E-Transactions actif

### Procédure d'installation

1. Copiez le dossier `payment_up2pay` dans votre répertoire de modules Odoo
2. Mettez à jour la liste des applications :
   ```
   Apps → Mise à jour de la liste des applications
   ```
3. Installez le module `Payment Up2pay` depuis la liste des applications
4. Configurez le fournisseur de paiement comme décrit ci-dessous

## ⚙️ Configuration

### Obtenir les identifiants Up2pay

Avant de configurer le module, assurez-vous d'avoir obtenu auprès d'Up2pay :

- **PBX_SITE** : L'identifiant du site
- **PBX_RANG** : Le rang de la boutique
- **PBX_IDENTIFIANT** : L'identifiant marchand
- **Clé HMAC** : La clé secrète en format hexadécimal pour la signature

### Configurer le fournisseur de paiement

1. Allez dans **Comptabilité → Configuration → Fournisseurs de paiement**
2. Sélectionnez **Up2pay** ou créez-en un nouveau
3. Remplissez les champs suivants :

   | Champ | Description | Exemple |
   |-------|-------------|---------|
   | Site ID (PBX_SITE) | Identifiant du site fourni par Up2pay | `12345678` |
   | Rank (PBX_RANG) | Rang de la boutique | `1` |
   | Merchant ID (PBX_IDENTIFIANT) | Identifiant marchand | `MERCHANT_ID` |
   | HMAC Key | Clé HMAC en hexadécimal | `A1B2C3D4...` |

4. Définissez l'état sur **Test** ou **Activé** selon votre environnement
5. Sauvegardez la configuration

### 🔐 Sécurité de la clé HMAC

La clé HMAC doit être fournie en format hexadécimal. Elle est utilisée pour signer les requêtes et vérifier les notifications. Ne partagez jamais cette clé.

## 🔧 Utilisation

### Effectuer un paiement

Une fois configuré, le module fonctionne automatiquement :

1. Lors du processus de checkout, sélectionnez **Up2pay** comme moyen de paiement
2. Le client est redirigé vers la plateforme sécurisée Up2pay
3. Après authentification, le client est redirigé vers votre site
4. La transaction est automatiquement mise à jour dans Odoo

### Gérer les transactions

Les transactions sont disponibles dans :
```
Comptabilité → Paiements → Transactions
```

Vous pouvez consulter :
- Le statut de chaque transaction
- Les détails de la réponse Up2pay
- Les codes d'autorisation et d'erreur

## 📁 Structure du module

```
payment_up2pay/
├── __init__.py                 # Initialisation du module
├── __manifest__.py             # Métadonnées du module
├── data/
│   └── payment_provider_data.xml    # Données de configuration
├── models/
│   ├── __init__.py
│   └── payment_provider.py          # Logique métier Up2pay
└── views/
    └── payment_provider_views.xml   # Vues de configuration
```

## 🔍 Détails techniques

### Signature HMAC

Le module implémente la signature HMAC-SHA512 selon les spécifications Up2pay :

- **Ordre des champs** : PBX_SITE, PBX_RANG, PBX_IDENTIFIANT, PBX_TOTAL, PBX_DEVISE, PBX_CMD, PBX_PORTEUR, PBX_RETOUR
- **Concaténation** : Sans séparateur
- **Clé** : Binaire convertie depuis l'hexadécimal stocké en base
- **Résultat** : Hexadécimal en majuscules

### Codes de retour

| Code | Signification |
|------|---------------|
| 00000 | Paiement accepté |
| Autre | Échec ou annulation (voir documentation Up2pay) |

### Devises supportées

- EUR (Euro) - Code ISO : 978
- USD (Dollar US) - Code ISO : 840
- GBP (Livre Sterling) - Code ISO : 826
- CHF (Franc Suisse) - Code ISO : 756
- CAD (Dollar Canadien) - Code ISO : 124

## 🐛 Dépannage

### Le paiement ne se déclenche pas

- Vérifiez que le fournisseur de paiement est en état **Activé**
- Confirmez que tous les champs obligatoires sont remplis
- Vérifiez les logs Odoo pour des erreurs de configuration

### Erreur de signature HMAC

- Assurez-vous que la clé HMAC est au bon format hexadécimal
- Vérifiez qu'il n'y a pas d'espaces dans la clé
- Confirmez que la clé correspond à votre environnement (test/production)

### Transaction non mise à jour

- Vérifiez que l'URL de notification est accessible depuis l'extérieur
- Consultez les logs pour les erreurs de vérification HMAC
- Assurez-vous que le pare-feu autorise les requêtes d'Up2pay

## 📞 Support

Pour toute question ou problème :

- Consultez la [documentation officielle Up2pay](https://www.e-transactions.fr/)
- Contactez le support technique d'Up2pay
- Ouvrez un ticket sur le dépôt GitHub du module

## 📄 Licence

Ce module est sous licence **LGPL-3** (GNU Lesser General Public License v3).

## 👥 Auteur

- **Auteur** : Your Company
- **Site web** : https://www.yourcompany.com

## 🔄 Version

- **Version** : 19.0.1.0.0
- **Compatibilité** : Odoo 19.0

---

**Note** : Ce module nécessite un contrat actif avec Up2pay E-Transactions. Assurez-vous de respecter les conditions d'utilisation et les spécifications techniques fournies par Up2pay.
