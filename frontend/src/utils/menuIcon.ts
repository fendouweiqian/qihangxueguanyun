const routeIcons: Record<string, string> = {
  education: 'education',
  platform: 'component',
  school: 'tree',
  'school-cache': 'table',
  tenant: 'peoples',
  student: 'user',
  order: 'form',
  task: 'job',
  'course-progress': 'chart',
  'face-media': 'user',
  ledger: 'money',
  recharge: 'money',
  'tiku-failure': 'bug',
  'runner-node': 'monitor',
  'runner-setting': 'edit'
};

const iconAliases: Record<string, string> = {
  camera: 'user',
  database: 'table',
  warning: 'bug'
};

/** 根据后台菜单元数据返回可渲染的图标名称，避免图标为空或不存在时出现空白菜单。 */
export const getMenuIcon = (icon?: string, path?: string, title?: string): string => {
  const normalizedIcon = String(icon || '').trim();
  if (normalizedIcon && normalizedIcon !== '#') return iconAliases[normalizedIcon] || normalizedIcon;
  const routeName = String(path || '').split('/').filter(Boolean).pop();
  if (routeName && routeIcons[routeName]) return routeIcons[routeName];
  const titleText = String(title || '');
  if (titleText.includes('教育')) return 'education';
  if (titleText.includes('学校')) return 'tree';
  if (titleText.includes('学员') || titleText.includes('用户')) return 'user';
  if (titleText.includes('租户')) return 'peoples';
  if (titleText.includes('任务')) return 'job';
  if (titleText.includes('订单')) return 'form';
  return 'component';
};
