# Enterprise Sales Analytics & Data Warehouse

## Problème métier
Une entreprise de distribution souhaite piloter sa performance
commerciale à partir de données dispersées. Ce projet construit un
entrepôt de données dimensionnel et un tableau de bord permettant
d'identifier les leviers de croissance et les zones de sous-performance.

## Données
- Source : Superstore Dataset (Kaggle)
- Volumétrie : 9 994 lignes, période 2014-2017
- Lien : https://www.kaggle.com/datasets/vivek468/superstore-dataset-final

## Architecture
CSV ==> Nettoyage Python (pandas) ==> PostgreSQL (schéma en étoile) ==> Power BI
Voir docs/schema_etoile.png

## Technologies
Python (pandas, sqlalchemy) ==> PostgreSQL ==> SQL avancé (CTE, fonctions fenêtre) ==> Power BI (DAX)

## Résultats clés
- Croissance du CA de +51% entre 2014 et 2017
- Identification des sous-catégories structurellement déficitaires : Bookcases (-3 472,56), Supplies (-1 188,99) et Tables (-17 725,59 )
- Segment Home Office : panier moyen le plus élevé malgré 18,7% des clients

## Recommandations
1. Auditer la politique tarifaire des Bookcases, Supplies et Tables
2. Prioriser le segment Home Office en fidélisation
3. Anticiper la saisonnalité de fin d'année dans la planification

## Structure du depot
01- enterprise -sales - analytics /
|-- README .md
|-- data /
|-- sql /
|-- etl /
|-- docs /
`-- screenshots /
## Comment reproduire
1. Creer la base : `createdb sales_analytics `
2. Executer le DDL : `psql -f sql /00 _ddl .sql `
3. Lancer l'ETL : `python etl / load_data .py `
4. Ouvrir le dashboard : `docs / dashboard .pbix `
## Auteur
 Ing Crespino Marius ADJANINYEDO -- [ LinkedIn: ] -- [ Email: cmadjaninyedo1@gmail.com ]