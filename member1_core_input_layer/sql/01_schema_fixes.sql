-- ============================================================
-- PlantQuest Schema Fixes
-- 負責人: 梁偉航
-- 目的: 修正原 Schema 審查時發現的 3 個問題
-- 執行方式: 貼到 Supabase SQL Editor 直接執行
-- ============================================================

-- ------------------------------------------------------------
-- 問題 1: plants 表的 mother_id / father_id 沒有循環引用防護
-- 風險: A 的母株是 B, B 的母株又被誤設成 A, 遞迴查詢族譜樹會死迴圈
-- 解法: BEFORE INSERT/UPDATE trigger, 往上追溯血緣鏈, 發現自我引用就擋下
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION check_plant_lineage_cycle()
RETURNS TRIGGER AS $$
DECLARE
    current_id uuid;
    depth int := 0;
    max_depth int := 20; -- 防止資料本身已髒污造成無限迴圈,強制上限
BEGIN
    -- 不能自己是自己的父母
    IF NEW.mother_id = NEW.id OR NEW.father_id = NEW.id THEN
        RAISE EXCEPTION 'plants: 植株不能是自己的母株或父株 (id=%)', NEW.id;
    END IF;

    -- 往上追溯 mother_id 鏈, 看是否會繞回 NEW.id
    current_id := NEW.mother_id;
    WHILE current_id IS NOT NULL AND depth < max_depth LOOP
        IF current_id = NEW.id THEN
            RAISE EXCEPTION 'plants: 偵測到母系血統循環引用 (id=%)', NEW.id;
        END IF;
        SELECT mother_id INTO current_id FROM plants WHERE id = current_id;
        depth := depth + 1;
    END LOOP;

    -- 往上追溯 father_id 鏈, 看是否會繞回 NEW.id
    current_id := NEW.father_id;
    depth := 0;
    WHILE current_id IS NOT NULL AND depth < max_depth LOOP
        IF current_id = NEW.id THEN
            RAISE EXCEPTION 'plants: 偵測到父系血統循環引用 (id=%)', NEW.id;
        END IF;
        SELECT father_id INTO current_id FROM plants WHERE id = current_id;
        depth := depth + 1;
    END LOOP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_plant_lineage_cycle ON plants;
CREATE TRIGGER trg_check_plant_lineage_cycle
    BEFORE INSERT OR UPDATE OF mother_id, father_id ON plants
    FOR EACH ROW
    EXECUTE FUNCTION check_plant_lineage_cycle();


-- ------------------------------------------------------------
-- 問題 2: compost_batches 只有 is_golden_ratio(布林), 但建豪 engine3.py
-- 的 calculate_compost_cn_ratio3() 實際回傳 4 種狀態字串:
-- "GOLDEN" / "TOO_WET" / "TOO_DRY" / "DATA_INCOMPLETE"
-- 解法: 新增 status 欄位存完整判定, is_golden_ratio 保留做快速篩選用
-- ------------------------------------------------------------

ALTER TABLE compost_batches
    ADD COLUMN IF NOT EXISTS status text;

COMMENT ON COLUMN compost_batches.status IS
    '對應 engine3.py 的判定結果: GOLDEN / TOO_WET / TOO_DRY / DATA_INCOMPLETE';

-- 用現有 is_golden_ratio 回填一個粗略的 status, 避免新欄位全部是 NULL
UPDATE compost_batches
SET status = CASE
    WHEN is_golden_ratio IS TRUE THEN 'GOLDEN'
    WHEN is_golden_ratio IS FALSE THEN 'OUT_OF_RANGE'
    ELSE NULL
END
WHERE status IS NULL;


-- ------------------------------------------------------------
-- 問題 3: updated_at 只有 plants 有欄位, 但沒有自動更新機制
-- 解法: 通用 trigger function, 之後任何表加了 updated_at 都能直接掛
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_plants_set_updated_at ON plants;
CREATE TRIGGER trg_plants_set_updated_at
    BEFORE UPDATE ON plants
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();


-- ------------------------------------------------------------
-- 附加: dictation_logs 建議索引 (核心輸入層會頻繁寫入與查詢狀態)
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_dictation_logs_status
    ON dictation_logs (status);

CREATE INDEX IF NOT EXISTS idx_dictation_logs_created_at
    ON dictation_logs (created_at DESC);
