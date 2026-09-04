<template>
  <div class="login-page">
    <div class="login-sheen"></div>
    <div class="login-shell">
      <section class="login-hero">
        <div class="brand">
          <img class="brand-logo" src="../assets/images/edu-platform-logo.svg" alt="启航学管云" />
          <div class="brand-text">
            <h1>启航学管云</h1>
            <p>机构学习视频自动化运营平台</p>
          </div>
        </div>
        <div class="hero-card">
          <h2>让学习进度可控，让培训交付更高效</h2>
          <p>
            面向培训机构的一站式刷课与进度管理系统，支持多租户开通，安全对接学员账号信息，自动完成学习视频进度维护。
          </p>
          <div class="hero-points">
            <div>
              <span>多租户</span>
              <strong>机构独立账号</strong>
            </div>
            <div>
              <span>自动化</span>
              <strong>定时刷课任务</strong>
            </div>
            <div>
              <span>可追溯</span>
              <strong>学习进度可视化</strong>
            </div>
          </div>
        </div>
      </section>
      <section class="login-panel">
        <el-form ref="loginRef" :model="loginForm" :rules="loginRules" class="login-form">
          <div class="title-box">
            <div class="panel-title">
              <h3>欢迎登录</h3>
              <p>机构管理端</p>
            </div>
          </div>
      <el-form-item v-if="tenantEnabled" prop="tenantId">
        <el-select v-model="loginForm.tenantId" filterable :placeholder="proxy.$t('login.selectPlaceholder')" style="width: 100%">
          <el-option v-for="item in tenantList" :key="item.tenantId" :label="item.companyName" :value="item.tenantId"></el-option>
          <template #prefix><svg-icon icon-class="company" class="el-input__icon input-icon" /></template>
        </el-select>
      </el-form-item>
      <el-form-item prop="username">
        <el-input v-model="loginForm.username" type="text" size="large" auto-complete="off" :placeholder="proxy.$t('login.username')">
          <template #prefix><svg-icon icon-class="user" class="el-input__icon input-icon" /></template>
        </el-input>
      </el-form-item>
      <el-form-item prop="password">
        <el-input
          v-model="loginForm.password"
          type="password"
          size="large"
          auto-complete="off"
          :placeholder="proxy.$t('login.password')"
          @keyup.enter="handleLogin"
        >
          <template #prefix><svg-icon icon-class="password" class="el-input__icon input-icon" /></template>
        </el-input>
      </el-form-item>
      <el-form-item v-if="captchaEnabled" prop="code">
        <el-input
          v-model="loginForm.code"
          size="large"
          auto-complete="off"
          :placeholder="proxy.$t('login.code')"
          style="width: 63%"
          @keyup.enter="handleLogin"
        >
          <template #prefix><svg-icon icon-class="validCode" class="el-input__icon input-icon" /></template>
        </el-input>
        <div class="login-code">
          <img :src="codeUrl" class="login-code-img" @click="getCode" />
        </div>
      </el-form-item>
      <el-checkbox v-model="loginForm.rememberMe" style="margin: 0 0 25px 0">{{ proxy.$t('login.rememberPassword') }}</el-checkbox>
      <el-form-item style="float: right">
        <el-button circle :title="proxy.$t('login.social.wechat')" @click="doSocialLogin('wechat')">
          <svg-icon icon-class="wechat" />
        </el-button>
      </el-form-item>
          <el-form-item style="width: 100%">
            <el-button :loading="loading" size="large" type="primary" style="width: 100%" @click.prevent="handleLogin">
              <span v-if="!loading">{{ proxy.$t('login.login') }}</span>
              <span v-else>{{ proxy.$t('login.logging') }}</span>
            </el-button>
            <div v-if="register" style="float: right">
              <router-link class="link-type" :to="'/register'">{{ proxy.$t('login.switchRegisterPage') }}</router-link>
            </div>
          </el-form-item>
          <div class="panel-help">登录即代表您同意平台服务规范与数据安全协议</div>
        </el-form>
      </section>
    </div>
    <div class="el-login-footer">
      <span>Copyright © 2018-2026 启航学管云 All Rights Reserved.</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { getCodeImg, getTenantList } from '@/api/login';
import { authRouterUrl } from '@/api/system/social/auth';
import { useUserStore } from '@/store/modules/user';
import { LoginData, TenantVO } from '@/api/types';
import { to } from 'await-to-js';
import { HttpStatus } from '@/enums/RespEnum';
import { useI18n } from 'vue-i18n';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;

const userStore = useUserStore();
const router = useRouter();
const { t } = useI18n();

const loginForm = ref<LoginData>({
  tenantId: '',
  username: '',
  password: '',
  rememberMe: false,
  code: '',
  uuid: ''
} as LoginData);

const loginRules: ElFormRules = {
  tenantId: [{ required: true, trigger: 'blur', message: t('login.rule.tenantId.required') }],
  username: [{ required: true, trigger: 'blur', message: t('login.rule.username.required') }],
  password: [{ required: true, trigger: 'blur', message: t('login.rule.password.required') }],
  code: [{ required: true, trigger: 'change', message: t('login.rule.code.required') }]
};

const codeUrl = ref('');
const loading = ref(false);
// 验证码开关
const captchaEnabled = ref(true);
// 租户开关
const tenantEnabled = ref(true);

// 注册开关
const register = ref(false);
const redirect = ref('/');
const loginRef = ref<ElFormInstance>();
// 租户列表
const tenantList = ref<TenantVO[]>([]);

watch(
  () => router.currentRoute.value,
  (newRoute: any) => {
    redirect.value = newRoute.query && newRoute.query.redirect && decodeURIComponent(newRoute.query.redirect);
  },
  { immediate: true }
);

const handleLogin = () => {
  loginRef.value?.validate(async (valid: boolean, fields: any) => {
    if (valid) {
      loading.value = true;
      // 勾选了需要记住密码设置在 localStorage 中设置记住用户名和密码
      if (loginForm.value.rememberMe) {
        localStorage.setItem('tenantId', String(loginForm.value.tenantId));
        localStorage.setItem('username', String(loginForm.value.username));
        localStorage.setItem('password', String(loginForm.value.password));
        localStorage.setItem('rememberMe', String(loginForm.value.rememberMe));
      } else {
        // 否则移除
        localStorage.removeItem('tenantId');
        localStorage.removeItem('username');
        localStorage.removeItem('password');
        localStorage.removeItem('rememberMe');
      }
      // 调用action的登录方法
      const [err] = await to(userStore.login(loginForm.value));
      if (!err) {
        const redirectUrl = redirect.value || '/';
        await router.push(redirectUrl);
        loading.value = false;
      } else {
        loading.value = false;
        // 重新获取验证码
        if (captchaEnabled.value) {
          await getCode();
        }
      }
    } else {
      console.log('error submit!', fields);
    }
  });
};

/**
 * 获取验证码
 */
const getCode = async () => {
  const { data } = await getCodeImg();
  captchaEnabled.value = data.captchaEnabled === undefined ? true : data.captchaEnabled;
  if (captchaEnabled.value) {
    // 刷新验证码时清空输入框
    loginForm.value.code = '';
    codeUrl.value = 'data:image/gif;base64,' + data.img;
    loginForm.value.uuid = data.uuid;
  }
};

const getLoginData = () => {
  const tenantId = localStorage.getItem('tenantId');
  const username = localStorage.getItem('username');
  const password = localStorage.getItem('password');
  const rememberMe = localStorage.getItem('rememberMe');
  loginForm.value = {
    tenantId: tenantId === null ? String(loginForm.value.tenantId) : tenantId,
    username: username === null ? String(loginForm.value.username) : username,
    password: password === null ? String(loginForm.value.password) : String(password),
    rememberMe: rememberMe === null ? false : Boolean(rememberMe)
  } as LoginData;
};

/**
 * 获取租户列表
 */
const initTenantList = async () => {
  const { data } = await getTenantList(false);
  tenantEnabled.value = data.tenantEnabled === undefined ? true : data.tenantEnabled;
  if (tenantEnabled.value) {
    tenantList.value = data.voList;
    if (tenantList.value != null && tenantList.value.length !== 0) {
      const rememberedTenantId = localStorage.getItem('tenantId');
      if (!rememberedTenantId) {
        const hasDefaultTenant = tenantList.value.some((item) => String(item.tenantId) === String(loginForm.value.tenantId));
        if (!hasDefaultTenant) {
          loginForm.value.tenantId = tenantList.value[0].tenantId;
        }
      }
    }
  }
};

/**
 * 第三方登录
 * @param type
 */
const doSocialLogin = (type: string) => {
  authRouterUrl(type, loginForm.value.tenantId).then((res: any) => {
    if (res.code === HttpStatus.SUCCESS) {
      // 获取授权地址跳转
      window.location.href = res.data;
    } else {
      ElMessage.error(res.msg);
    }
  });
};

onMounted(() => {
  getLoginData();
  getCode();
  initTenantList();
});
</script>

<style lang="scss" scoped>
.login-page {
  --brand-deep: #0b2b4f;
  --brand-mid: #154a7a;
  --brand-accent: #2fb4d6;
  --text-strong: #0f172a;
  --text-muted: #637084;
  --panel-bg: rgba(255, 255, 255, 0.92);
  position: relative;
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px 80px;
  background: linear-gradient(135deg, #0b2447 0%, #0f3d63 45%, #1d6e8a 100%);
  overflow: hidden;
}

.login-sheen {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 20%, rgba(47, 180, 214, 0.22), transparent 45%),
    radial-gradient(circle at 75% 10%, rgba(66, 135, 245, 0.18), transparent 48%),
    radial-gradient(circle at 90% 80%, rgba(10, 145, 180, 0.2), transparent 55%);
  pointer-events: none;
}

.login-shell {
  position: relative;
  z-index: 1;
  width: min(1120px, 100%);
  display: grid;
  grid-template-columns: 1.25fr 0.9fr;
  gap: 32px;
  align-items: center;
}

.login-hero {
  color: #f8fbff;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 16px;
}

.brand-logo {
  width: 68px;
  height: 68px;
}

.brand-text h1 {
  font-size: 34px;
  font-weight: 700;
  margin: 0 0 6px;
  letter-spacing: 2px;
}

.brand-text p {
  margin: 0;
  font-size: 16px;
  color: rgba(248, 251, 255, 0.8);
  letter-spacing: 1px;
}

.hero-card {
  background: rgba(14, 38, 66, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 22px;
  padding: 28px 28px 24px;
  backdrop-filter: blur(6px);
  box-shadow: 0 24px 60px rgba(3, 10, 20, 0.35);
}

.hero-card h2 {
  margin: 0 0 12px;
  font-size: 22px;
  font-weight: 600;
}

.hero-card p {
  margin: 0 0 20px;
  color: rgba(248, 251, 255, 0.78);
  line-height: 1.7;
  font-size: 14px;
}

.hero-points {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.hero-points div {
  background: rgba(15, 34, 55, 0.55);
  border-radius: 14px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.hero-points span {
  font-size: 12px;
  color: rgba(248, 251, 255, 0.6);
}

.hero-points strong {
  font-size: 14px;
  font-weight: 600;
  color: #f8fbff;
}

.login-panel {
  display: flex;
  justify-content: center;
}

.login-form {
  width: min(420px, 100%);
  background: var(--panel-bg);
  border-radius: 20px;
  padding: 28px 28px 18px;
  box-shadow:
    0 24px 60px rgba(5, 16, 32, 0.35),
    inset 0 0 0 1px rgba(255, 255, 255, 0.2);
  .el-input {
    height: 42px;
    input {
      height: 42px;
    }
  }

  .input-icon {
    height: 41px;
    width: 14px;
    margin-left: 0px;
  }
}

.title-box {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  margin-bottom: 24px;
}

.panel-title h3 {
  margin: 0;
  font-size: 20px;
  color: var(--text-strong);
}

.panel-title p {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--text-muted);
}

.panel-help {
  margin-top: 6px;
  font-size: 12px;
  color: #8b97a6;
  text-align: center;
}

.login-code {
  width: 33%;
  height: 40px;
  float: right;

  img {
    cursor: pointer;
    vertical-align: middle;
  }
}

.el-login-footer {
  height: 40px;
  line-height: 40px;
  position: fixed;
  bottom: 0;
  width: 100%;
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
  font-family: 'Trebuchet MS', Arial, sans-serif;
  font-size: 12px;
  letter-spacing: 1px;
}

.login-code-img {
  height: 40px;
  padding-left: 12px;
}

@media (max-width: 992px) {
  .login-shell {
    grid-template-columns: 1fr;
  }

  .login-hero {
    order: 2;
  }
}

@media (max-width: 640px) {
  .login-page {
    padding: 24px 16px 80px;
  }

  .hero-card {
    padding: 22px;
  }

  .hero-points {
    grid-template-columns: 1fr;
  }
}
</style>
