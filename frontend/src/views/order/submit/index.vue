<template>
  <div class="p-2">
    <el-card shadow="never">
      <el-empty description="正在打开提交订单窗口..." />
    </el-card>
  </div>
</template>

<script setup name="OrderSubmit" lang="ts">
import type { RouteLocationNormalizedLoaded } from 'vue-router';
import { useTagsViewStore } from '@/store/modules/tagsView';

const router = useRouter();
const route = useRoute();
const tagsViewStore = useTagsViewStore();

/** 清理旧提交订单兼容页在标签栏中产生的临时页签。 */
const closeSubmitRouteTag = async (submitRoute: RouteLocationNormalizedLoaded) => {
  await tagsViewStore.delView(submitRoute as any);
};

onMounted(async () => {
  const submitRoute = { ...route };
  await closeSubmitRouteTag(submitRoute);
  await router.replace({
    path: '/order/courseProgress',
    query: { openSubmit: '1' }
  });
  await closeSubmitRouteTag(submitRoute);
});
</script>
