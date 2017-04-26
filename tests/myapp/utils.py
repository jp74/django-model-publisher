def create_models_from_app(app_name):
    """
    Manually create Models (used only for testing) from the specified string app name.
    Models are loaded from the module "<app_name>.models"
    """
    from django.db import connection, DatabaseError
    from django.db.models.loading import load_app
    from django.core.management import sql
    from django.core.management.color import no_style

    app = load_app(app_name)
    sql = sql.sql_create(app, no_style(), connection)
    cursor = connection.cursor()
    for statement in sql:
        try:
            cursor.execute(statement)
        except DatabaseError:
            pass
