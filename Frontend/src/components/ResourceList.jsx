/**
 * AEGIS — Resource List Component
 * Shows seeded resources with availability status.
 */

export default function ResourceList({ resources }) {
  if (resources.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state__icon">📦</div>
        <div className="empty-state__text">No resources loaded.</div>
      </div>
    );
  }

  const typeIcons = { medical: '🚑', rescue: '🚤', food: '🍞', shelter: '🏠' };

  return (
    <div>
      {resources.map(resource => (
        <div key={resource.id} className="resource-item">
          <div className={`resource-item__dot resource-item__dot--${resource.status}`} />
          <div className="resource-item__info">
            <div className="resource-item__name">
              {typeIcons[resource.type] || '📋'} {resource.name}
            </div>
            <div className="resource-item__type">
              {resource.type} • {resource.status}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
