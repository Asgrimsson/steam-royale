# Varanleg vistun gagna

Ef nemendur missa alla vinnu við restart/redeploy er gagnagrunnurinn ekki á varanlegri geymslu.

## Lausn A - einföldust núna

Uppfærðu Render þjónustuna í paid instance og bættu við Persistent Disk.

Environment variable:

```text
DATA_DIR=/opt/render/project/src/data
```

Persistent Disk:

```text
Name: skola-royale-data
Mount path: /opt/render/project/src/data
Size: 1 GB
```

## Lausn B - best til lengri tíma

Færa gögn í PostgreSQL. Það væri næsta útgáfa, t.d. v1.2 PostgreSQL.
