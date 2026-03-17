from django.db import migrations, models
import django.db.models.deletion


def _backfill_classplan_subjects(apps, schema_editor):
    ClassPlanConfig = apps.get_model("core", "ClassPlanConfig")
    SubjectConfig = apps.get_model("core", "SubjectConfig")
    ClassGroup = apps.get_model("core", "ClassGroup")

    # 每个组织准备一个兜底科目配置（仅在该组织没有任何科目时创建）
    fallback_by_org = {}
    for cp in ClassPlanConfig.objects.filter(subjects__isnull=True).order_by("id"):
        subject_id = None

        # 优先沿用已关联班级组中的科目绑定
        linked_group = ClassGroup.objects.filter(
            linked_class_plan_id=cp.id,
            linked_subjects_id__isnull=False,
        ).order_by("id").first()
        if linked_group:
            subject_id = linked_group.linked_subjects_id

        # 其次取同组织下第一个已有科目配置
        if subject_id is None:
            first_subject = SubjectConfig.objects.filter(
                organization_id=cp.organization_id
            ).order_by("id").first()
            if first_subject:
                subject_id = first_subject.id

        # 若组织下没有科目，自动创建一个兜底科目
        if subject_id is None:
            if cp.organization_id not in fallback_by_org:
                fallback = SubjectConfig.objects.create(
                    organization_id=cp.organization_id,
                    name="自动生成科目配置",
                    identifier=f"auto-subjects-org-{cp.organization_id}",
                    data_json={"Name": "自动生成科目配置", "Subjects": {}},
                )
                fallback_by_org[cp.organization_id] = fallback.id
            subject_id = fallback_by_org[cp.organization_id]

        cp.subjects_id = subject_id
        cp.save(update_fields=["subjects"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_update_default_management_ports"),
    ]

    operations = [
        migrations.AddField(
            model_name="classplanconfig",
            name="subjects",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="class_plans",
                to="core.subjectconfig",
                verbose_name="依赖科目",
            ),
        ),
        migrations.RunPython(_backfill_classplan_subjects, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="classplanconfig",
            name="subjects",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="class_plans",
                to="core.subjectconfig",
                verbose_name="依赖科目",
            ),
        ),
    ]
