import { createWebHistory, createRouter, RouteRecordRaw } from 'vue-router';
/* Layout */
import Layout from '@/layout/index.vue';

/**
 * Note: 路由配置项
 *
 * hidden: true                     // 当设置 true 的时候该路由不会再侧边栏出现 如401，login等页面，或者如一些编辑页面/edit/1
 * alwaysShow: true                 // 当你一个路由下面的 children 声明的路由大于1个时，自动会变成嵌套的模式--如组件页面
 *                                  // 只有一个时，会将那个子路由当做根路由显示在侧边栏--如引导页面
 *                                  // 若你想不管路由下面的 children 声明的个数都显示你的根路由
 *                                  // 你可以设置 alwaysShow: true，这样它就会忽略之前定义的规则，一直显示根路由
 * redirect: noRedirect             // 当设置 noRedirect 的时候该路由在面包屑导航中不可被点击
 * name:'router-name'               // 设定路由的名字，一定要填写不然使用<keep-alive>时会出现各种问题
 * query: '{"id": 1, "name": "ry"}' // 访问路由的默认传递参数
 * roles: ['admin', 'common']       // 访问路由的角色权限
 * permissions: ['a:a:a', 'b:b:b']  // 访问路由的菜单权限
 * meta : {
    noCache: true                   // 如果设置为true，则不会被 <keep-alive> 缓存(默认 false)
    title: 'title'                  // 设置该路由在侧边栏和面包屑中展示的名字
    icon: 'svg-name'                // 设置该路由的图标，对应路径src/assets/icons/svg
    breadcrumb: false               // 如果设置为false，则不会在breadcrumb面包屑中显示
    activeMenu: '/system/user'      // 当路由设置了该属性，则会高亮相对应的侧边栏。
  }
 */

// 公共路由
export const constantRoutes: RouteRecordRaw[] = [
  {
    path: '/redirect',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '/redirect/:path(.*)',
        component: () => import('@/views/redirect/index.vue')
      }
    ]
  },
  {
    path: '/social-callback',
    hidden: true,
    component: () => import('@/layout/components/SocialCallback/index.vue')
  },
  {
    path: '/login',
    component: () => import('@/views/login.vue'),
    hidden: true
  },
  {
    path: '/register',
    component: () => import('@/views/register.vue'),
    hidden: true
  },
  {
    path: '/:pathMatch(.*)*',
    component: () => import('@/views/error/404.vue'),
    hidden: true
  },
  {
    path: '/401',
    component: () => import('@/views/error/401.vue'),
    hidden: true
  },
  {
    path: '',
    component: Layout,
    redirect: '/index',
    children: [
      {
        path: '/index',
        component: () => import('@/views/index.vue'),
        name: 'Index',
        meta: { title: '首页', icon: 'dashboard', affix: true }
      }
    ]
  },
  {
    path: '/education',
    component: Layout,
    redirect: '/education/student',
    name: 'Education',
    alwaysShow: true,
    meta: { title: '教育业务', icon: 'education' },
    children: [
      { path: 'student', component: () => import('@/views/education/student/index.vue'), name: 'EduStudent', meta: { title: '学员管理', icon: 'user' } },
      { path: 'school', component: () => import('@/views/education/school/index.vue'), name: 'EduSchool', meta: { title: '学校管理', icon: 'tree' } },
      { path: 'platform', component: () => import('@/views/education/platform/index.vue'), name: 'EduPlatform', meta: { title: '平台管理', icon: 'international' } },
      { path: 'order', component: () => import('@/views/education/order/index.vue'), name: 'EduOrder', meta: { title: '订单管理', icon: 'form' } },
      { path: 'course-progress', component: () => import('@/views/education/course-progress/index.vue'), name: 'EduCourseProgress', meta: { title: '课程进度', icon: 'chart' } },
      { path: 'task', component: () => import('@/views/education/task/index.vue'), name: 'EduTask', meta: { title: '任务管理', icon: 'list' } },
      { path: 'face-media', component: () => import('@/views/education/face-media/index.vue'), name: 'EduFaceMedia', meta: { title: '人脸媒体', icon: 'camera' } },
      { path: 'runner-node', component: () => import('@/views/education/runner-node/index.vue'), name: 'EduRunnerNode', meta: { title: '执行节点', icon: 'server' } },
      { path: 'runner-setting', component: () => import('@/views/education/runner-setting/index.vue'), name: 'EduRunnerSetting', meta: { title: '执行配置', icon: 'tool' } },
      { path: 'school-cache', component: () => import('@/views/education/school-cache/index.vue'), name: 'EduSchoolCache', meta: { title: '学校缓存', icon: 'database' } },
      { path: 'tenant', component: () => import('@/views/education/tenant/index.vue'), name: 'EduTenant', meta: { title: '租户管理', icon: 'peoples' } },
      { path: 'recharge', component: () => import('@/views/education/recharge/index.vue'), name: 'EduRecharge', meta: { title: '充值管理', icon: 'money' } },
      { path: 'ledger', component: () => import('@/views/education/ledger/index.vue'), name: 'EduLedger', meta: { title: '积分流水', icon: 'documentation' } },
      { path: 'tiku-failure', component: () => import('@/views/education/tiku-failure/index.vue'), name: 'EduTikuFailure', meta: { title: '题库失败', icon: 'warning' } }
    ]
  },
  {
    path: '/user',
    component: Layout,
    hidden: true,
    redirect: 'noredirect',
    children: [
      {
        path: 'profile',
        component: () => import('@/views/system/user/profile/index.vue'),
        name: 'Profile',
        meta: { title: '个人中心', icon: 'user' }
      }
    ]
  }
];

// 动态路由，基于用户权限动态去加载
export const dynamicRoutes: RouteRecordRaw[] = [

];

/**
 * 创建路由
 */
const router = createRouter({
  history: createWebHistory(import.meta.env.VITE_APP_CONTEXT_PATH),
  routes: constantRoutes,
  // 刷新时，滚动条位置还原
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }
    return { top: 0 };
  }
});

export default router;
