#!/usr/bin/env bash
# Script de build exécuté par Render à chaque déploiement
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
# Premier déploiement uniquement : jeu de données fictif + comptes de démonstration
# (ne réécrase jamais des données importées ensuite par le CIAT)
python manage.py shell -c "from pilotage.models import Projet; import sys; sys.exit(0 if Projet.objects.exists() else 1)" \
  || python manage.py seed_demo
