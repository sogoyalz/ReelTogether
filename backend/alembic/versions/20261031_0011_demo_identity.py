"""Isolate verified legacy demo identities from the live TMDB namespace.

Internal movie IDs and all user references are preserved. Ambiguous/provider-
modified records are left untouched for manual review. Downgrade deliberately
keeps repaired IDs, since restoring collisions would corrupt provider identity.
"""
from alembic import op
import sqlalchemy as sa
revision = '20261031_0011'
down_revision = '20260916_0010'
branch_labels = None
depends_on = None
DEMOS = [(1, 8725851, 'oppenheimer', 'Oppenheimer', 'https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?auto=format&fit=crop&w=800&q=80'), (2, 8725852, 'barbie', 'Barbie', 'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=800&q=80'), (3, 8725853, 'spider-man-no-way-home', 'Spider-Man: No Way Home', 'https://images.unsplash.com/photo-1531259683007-016a7b628fc3?auto=format&fit=crop&w=800&q=80'), (4, 8725854, 'top-gun-maverick', 'Top Gun: Maverick', 'https://images.unsplash.com/photo-1504198458649-3128b932f49b?auto=format&fit=crop&w=800&q=80'), (5, 8725855, 'avatar-the-way-of-water', 'Avatar: The Way of Water', 'https://images.unsplash.com/photo-1440404653325-ab127d49abc1?auto=format&fit=crop&w=800&q=80'), (6, 8725856, 'inside-out-2', 'Inside Out 2', 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=800&q=80'), (7, 872585, 'dune-part-two', 'Dune: Part Two', 'https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=800&q=80'), (8, 1022789, 'the-batman-part-ii', 'The Batman Part II', 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=800&q=80'), (9, 299536, 'avengers-secret-wars', 'Avengers: Secret Wars', 'https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?auto=format&fit=crop&w=800&q=80'), (10, 447365, 'guardians-of-the-galaxy-rebirth', 'Guardians of the Galaxy: Rebirth', 'https://images.unsplash.com/photo-1499364615650-ec38552f4f34?auto=format&fit=crop&w=800&q=80'), (11, 901362, 'spider-man-new-day', 'Spider-Man: New Day', 'https://images.unsplash.com/photo-1518733057094-95b53143d2a7?auto=format&fit=crop&w=800&q=80'), (12, 938614, 'inside-out-3', 'Inside Out 3', 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=800&q=80'), (13, 8725857, 'superman-legacy', 'Superman: Legacy', 'https://images.unsplash.com/photo-1542204625-de293a2f8ff0?auto=format&fit=crop&w=800&q=80'), (14, 8725858, 'the-fantastic-four-first-steps', 'The Fantastic Four: First Steps', 'https://images.unsplash.com/photo-1535016120720-40c646be5580?auto=format&fit=crop&w=800&q=80'), (15, 8725859, 'shrek-5', 'Shrek 5', 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=800&q=80'), (16, 8725860, 'toy-story-5', 'Toy Story 5', 'https://images.unsplash.com/photo-1511497584788-876760111969?auto=format&fit=crop&w=800&q=80')]


def upgrade():
    movies = sa.table('movies', sa.column('id', sa.Integer), sa.column('tmdb_id', sa.Integer),
        sa.column('slug', sa.String), sa.column('title', sa.String), sa.column('poster_url', sa.String),
        sa.column('genres', sa.JSON), sa.column('provider_metadata', sa.JSON))
    bind = op.get_bind()
    for index, old_id, slug, title, poster in DEMOS:
        row = bind.execute(sa.select(movies).where(movies.c.tmdb_id == old_id,
            movies.c.slug == slug, movies.c.title == title, movies.c.poster_url == poster)).mappings().first()
        if row is None:
            continue
        # Negative IDs are reserved for demo content; refuse unexpected collisions.
        if bind.execute(sa.select(movies.c.id).where(movies.c.tmdb_id == -index)).first():
            raise RuntimeError('Demo identity namespace collision; inspect before upgrading')
        metadata = dict(row['provider_metadata'] or {})
        metadata['catalog_source'] = 'demo'
        genres = ['Science Fiction' if g == 'Sci-Fi' else g for g in (row['genres'] or [])]
        bind.execute(movies.update().where(movies.c.id == row['id']).values(
            tmdb_id=-index, genres=genres, provider_metadata=metadata))


def downgrade():
    pass
