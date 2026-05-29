-- ═══════════════════════════════════════════════════════════════
-- Auto-generated SQL JOIN queries from dbt lineage YAML
-- Generated for silver_layer models with Neo4j lineage mapping
-- ═══════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_Eway_Report
-- File: models/HubOps_Dashboard/t3_Eway_Report.sql
-- Columns: 13 | Upstreams: 4
-- ═══════════════════════════════════════════════

SELECT
  t.awb_number,  -- t2_master_hubops_bk.awb_number
  t.Eway_bill_no,  -- t1_ewbs_ewaybill_data_hubops.ewaybill_no
  t.awb_Booking_date,  -- t2_master_hubops_bk.booking_complete_time
  t.Eway_bill_generated_date,  -- t1_ewbs_ewaybill_data_hubops.eway_bill_crt_date
  t.Eway_bill_expiry_date,  -- t1_ewbs_ewaybill_data_hubops.ewb_bill_exp_date
  t.booking_cp_id,  -- t2_master_hubops_bk.origin_cp_id
  t.booking_cp_name,  -- t2_master_hubops_bk.origin_cp_name
  t.hub_id,  -- t2_master_hubops_bk.origin_hub_id
  t.booking_hub_name,  -- t2_master_hubops_bk.origin_hub_name
  t.zone,  -- t2_master_hubops_bk.origin_zone
  t.current_location,  -- t2_master_hubops.premise_name
  t.part_b_updated_time,  -- t1_ewbs_ewaybill_data_hubops.update_date
  t.part_b_updated_hub  -- t1_ewbs_ewaybill_data_hubops.ewb_opr_place
FROM silver_layer.t3_Eway_Report t
LEFT JOIN silver_layer.t2_master_hubops_bk t2_master_hubops_bk
  ON
    t.awb_number = t2_master_hubops_bk.awb_number AND
    t.awb_Booking_date = t2_master_hubops_bk.booking_complete_time AND
    t.booking_cp_id = t2_master_hubops_bk.origin_cp_id AND
    t.booking_cp_name = t2_master_hubops_bk.origin_cp_name AND
    t.hub_id = t2_master_hubops_bk.origin_hub_id AND
    t.booking_hub_name = t2_master_hubops_bk.origin_hub_name AND
    t.zone = t2_master_hubops_bk.origin_zone
LEFT JOIN silver_layer.t1_ewbs_ewaybill_data_hubops t1_ewbs_ewaybill_dat
  ON
    t.Eway_bill_no = t1_ewbs_ewaybill_dat.ewaybill_no AND
    t.Eway_bill_generated_date = t1_ewbs_ewaybill_dat.eway_bill_crt_date AND
    t.Eway_bill_expiry_date = t1_ewbs_ewaybill_dat.ewb_bill_exp_date AND
    t.part_b_updated_time = t1_ewbs_ewaybill_dat.update_date AND
    t.part_b_updated_hub = t1_ewbs_ewaybill_dat.ewb_opr_place
LEFT JOIN silver_layer.t2_master_hubops t2_master_hubops
  ON
    t.current_location = t2_master_hubops.premise_name

-- WHERE 1=1
--   AND t.<column> = '<value>'


-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_Fastrack_orders_report
-- File: models/HubOps_Dashboard/t3_Fastrack_orders_report.sql
-- Columns: 24 | Upstreams: 2
-- ═══════════════════════════════════════════════

SELECT
  t.documentno,
  t.booking_date,
  t.booking_cp_id,  -- t2_master_hubops_bk.origin_cp_id
  t.booking_cp,  -- t2_master_hubops_bk.origin_cp_name
  t.parent_hub_id,  -- t2_master_hubops_bk.origin_hub_id
  t.parent_hub_name,  -- t2_master_hubops_bk.origin_hub_name
  t.from_state,  -- t2_master_hubops_bk.origin_state
  t.to_pincode,
  t.to_city,  -- t2_master_hubops_bk.destination_city
  t.to_state,  -- t2_master_hubops_bk.destination_state
  t.destination_hub_name,  -- t2_master_hubops_bk.destination_hub_name
  t.to_center_name,  -- t2_master_hubops_bk.to_center_name
  t.receiver_name,  -- t2_master_hubops_bk.receiver_name
  t.booking_type,
  t.service_type,
  t.document_type,
  t.travel_by,
  t.booking_weight,
  t.charges,
  t.Zone,  -- t2_master_hubops_bk.origin_zone
  t.status,  -- t2_master_hubops_bk.status
  t.deliverydate,  -- t2_master_hubops_bk.operation_time
  t.current_premise_name,  -- t2_master_hubops_bk.current_premise_name
  t.POD
FROM silver_layer.t3_Fastrack_orders_report t
LEFT JOIN silver_layer.t2_master_hubops_bk t2_master_hubops_bk
  ON
    t.booking_cp_id = t2_master_hubops_bk.origin_cp_id AND
    t.booking_cp = t2_master_hubops_bk.origin_cp_name AND
    t.parent_hub_id = t2_master_hubops_bk.origin_hub_id AND
    t.parent_hub_name = t2_master_hubops_bk.origin_hub_name AND
    t.from_state = t2_master_hubops_bk.origin_state AND
    t.to_city = t2_master_hubops_bk.destination_city AND
    t.to_state = t2_master_hubops_bk.destination_state AND
    t.destination_hub_name = t2_master_hubops_bk.destination_hub_name AND
    t.to_center_name = t2_master_hubops_bk.to_center_name AND
    t.receiver_name = t2_master_hubops_bk.receiver_name AND
    t.Zone = t2_master_hubops_bk.origin_zone AND
    t.status = t2_master_hubops_bk.status AND
    t.deliverydate = t2_master_hubops_bk.operation_time AND
    t.current_premise_name = t2_master_hubops_bk.current_premise_name

-- WHERE 1=1
--   AND t.<column> = '<value>'


-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_HUB_Audit_Entry_Report_dataset
-- File: models/HubOps_Dashboard/t3_HUB_Audit_Entry_Report_dataset.sql
-- Columns: 26 | Upstreams: 3
-- ═══════════════════════════════════════════════

SELECT
  t.document_no,
  t.booking_date,  -- t2_master_hubops_bk.booking_date
  t.from_center,  -- t2_master_hubops_bk.from_center
  t.to_center,  -- t2_master_hubops_bk.to_center
  t.document_type,  -- t2_master_hubops_bk.document_type
  t.service_type,  -- t2_master_hubops_bk.service_type
  t.travel_by,  -- t2_master_hubops_bk.travel_by
  t.charges,  -- t2_master_hubops_bk.charges
  t.invoice_no,
  t.sender,  -- t2_master_hubops_bk.sender_name
  t.receiver,  -- t2_master_hubops_bk.receiver_name
  t.booking_weight,  -- t1_aus_audit_event_hubops.booked_weight
  t.audited_weight,  -- t1_aus_audit_event_hubops.audited_weight
  t.weight_difference,  -- t1_aus_audit_event_hubops.weight_difference
  t.weight_difference_percentage,  -- t1_aus_audit_event_hubops.weight_difference_percentage
  t.volumetric_booked_weight,  -- t1_aus_audit_event_hubops.volumetric_booked_weight
  t.volumetric_audited_weight,  -- t1_aus_audit_event_hubops.volumetric_audited_weight
  t.audited_hub_id,  -- t1_aus_audit_event_hubops.audited_hub_id
  t.audited_hub,  -- t1_aus_audit_event_hubops.audited_hub
  t.length,  -- t1_aus_audit_event_hubops.length
  t.width,  -- t1_aus_audit_event_hubops.width
  t.height,  -- t1_aus_audit_event_hubops.height
  t.booking_type,  -- t2_master_hubops_bk.cash_account
  t.manual_auto,  -- t1_aus_audit_event_hubops.manual_auto
  t.status,  -- t1_aus_audit_event_hubops.status
  t.audit_date  -- t1_aus_audit_event_hubops.create_ts
FROM silver_layer.t3_HUB_Audit_Entry_Report_dataset t
LEFT JOIN silver_layer.t2_master_hubops_bk t2_master_hubops_bk
  ON
    t.booking_date = t2_master_hubops_bk.booking_date AND
    t.from_center = t2_master_hubops_bk.from_center AND
    t.to_center = t2_master_hubops_bk.to_center AND
    t.document_type = t2_master_hubops_bk.document_type AND
    t.service_type = t2_master_hubops_bk.service_type AND
    t.travel_by = t2_master_hubops_bk.travel_by AND
    t.charges = t2_master_hubops_bk.charges AND
    t.sender = t2_master_hubops_bk.sender_name AND
    t.receiver = t2_master_hubops_bk.receiver_name AND
    t.booking_type = t2_master_hubops_bk.cash_account
LEFT JOIN silver_layer.t1_aus_audit_event_hubops t1_aus_audit_event_h
  ON
    t.booking_weight = t1_aus_audit_event_h.booked_weight AND
    t.audited_weight = t1_aus_audit_event_h.audited_weight AND
    t.weight_difference = t1_aus_audit_event_h.weight_difference AND
    t.weight_difference_percentage = t1_aus_audit_event_h.weight_difference_percentage AND
    t.volumetric_booked_weight = t1_aus_audit_event_h.volumetric_booked_weight AND
    t.volumetric_audited_weight = t1_aus_audit_event_h.volumetric_audited_weight AND
    t.audited_hub_id = t1_aus_audit_event_h.audited_hub_id AND
    t.audited_hub = t1_aus_audit_event_h.audited_hub AND
    t.length = t1_aus_audit_event_h.length AND
    t.width = t1_aus_audit_event_h.width AND
    t.height = t1_aus_audit_event_h.height AND
    t.manual_auto = t1_aus_audit_event_h.manual_auto AND
    t.status = t1_aus_audit_event_h.status AND
    t.audit_date = t1_aus_audit_event_h.create_ts

-- WHERE 1=1
--   AND t.<column> = '<value>'


-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_booking_data_vs_status_report
-- File: models/HubOps_Dashboard/t3_booking_data_vs_status_report.sql
-- Columns: 18 | Upstreams: 3
-- ═══════════════════════════════════════════════

SELECT
  t.shipment_no,
  t.booking_datetime,  -- t2_master_hubops_bk.booking_datetime
  t.from_hub_id,  -- t2_master_hubops_bk.src_hub_id
  t.from_hub,  -- t2_master_hubops_bk.src_hub_name
  t.from_cp_id,  -- t2_master_hubops_bk.src_cp_id
  t.from_cp,  -- t2_master_hubops_bk.src_cp_name
  t.from_pincode,  -- t2_master_hubops_bk.pickup_pincode
  t.audited_weight,  -- t1_aus_audit_event_hubops.audited_weight
  t.product_type,  -- t2_master_hubops_bk.product_type
  t.booking_type,  -- t2_master_hubops_bk.booking_type
  t.transport_mode,  -- t2_master_hubops_bk.transport_mode
  t.to_hub_id,  -- t2_master_hubops_bk.destination_hub_id
  t.to_hub_name,  -- t2_master_hubops_bk.destination_hub_name
  t.to_cp_name,  -- t2_master_hubops_bk.destination_cp_name
  t.to_pincode,  -- t2_master_hubops_bk.destination_pincode
  t.status,
  t.current_premise_name,  -- t2_master_hubops.current_premise_name
  t.current_status  -- t2_master_hubops.current_status
FROM silver_layer.t3_booking_data_vs_status_report t
LEFT JOIN silver_layer.t2_master_hubops t2_master_hubops
  ON
    t.current_premise_name = t2_master_hubops.current_premise_name AND
    t.current_status = t2_master_hubops.current_status
LEFT JOIN silver_layer.t2_master_hubops_bk t2_master_hubops_bk
  ON
    t.booking_datetime = t2_master_hubops_bk.booking_datetime AND
    t.from_hub_id = t2_master_hubops_bk.src_hub_id AND
    t.from_hub = t2_master_hubops_bk.src_hub_name AND
    t.from_cp_id = t2_master_hubops_bk.src_cp_id AND
    t.from_cp = t2_master_hubops_bk.src_cp_name AND
    t.from_pincode = t2_master_hubops_bk.pickup_pincode AND
    t.product_type = t2_master_hubops_bk.product_type AND
    t.booking_type = t2_master_hubops_bk.booking_type AND
    t.transport_mode = t2_master_hubops_bk.transport_mode AND
    t.to_hub_id = t2_master_hubops_bk.destination_hub_id AND
    t.to_hub_name = t2_master_hubops_bk.destination_hub_name AND
    t.to_cp_name = t2_master_hubops_bk.destination_cp_name AND
    t.to_pincode = t2_master_hubops_bk.destination_pincode
LEFT JOIN silver_layer.t1_aus_audit_event_hubops t1_aus_audit_event_h
  ON
    t.audited_weight = t1_aus_audit_event_h.audited_weight

-- WHERE 1=1
--   AND t.<column> = '<value>'


-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_booking_vs_delivery_report
-- File: models/HubOps_Dashboard/t3_booking_vs_delivery_report.sql
-- Columns: 16 | Upstreams: 3
-- ═══════════════════════════════════════════════

SELECT
  t.documentno,
  t.booking_datetime,  -- t2_master_hubops_bk.booking_datetime
  t.delivery_date,
  t.charges,  -- t2_master_hubops_bk.charges
  t.document_type,  -- t2_master_hubops_bk.document_type
  t.booking_type,  -- t2_master_hubops_bk.booking_type
  t.booking_cp_id,  -- t2_master_hubops_bk.booking_cp_id
  t.booking_cp,  -- t2_master_hubops_bk.booking_cp_name
  t.from_hub_id,  -- t2_master_hubops_bk.from_hub_id
  t.from_hub,
  t.from_center,
  t.state,
  t.to_center,
  t.sender,  -- t1_ss_address_details_hubops.sender_name
  t.receiver,  -- t1_ss_address_details_hubops.receiver_name
  t.status  -- t1_drs_orderdeliveryevents_final_fulfill_6M.status
FROM silver_layer.t3_booking_vs_delivery_report t
LEFT JOIN silver_layer.t2_master_hubops_bk t2_master_hubops_bk
  ON
    t.booking_datetime = t2_master_hubops_bk.booking_datetime AND
    t.charges = t2_master_hubops_bk.charges AND
    t.document_type = t2_master_hubops_bk.document_type AND
    t.booking_type = t2_master_hubops_bk.booking_type AND
    t.booking_cp_id = t2_master_hubops_bk.booking_cp_id AND
    t.booking_cp = t2_master_hubops_bk.booking_cp_name AND
    t.from_hub_id = t2_master_hubops_bk.from_hub_id
LEFT JOIN silver_layer.t1_drs_orderdeliveryevents_final_fulfill_6M t1_drs_orderdelivery
  ON
    t.status = t1_drs_orderdelivery.status
LEFT JOIN silver_layer.t1_ss_address_details_hubops t1_ss_address_detail
  ON
    t.sender = t1_ss_address_detail.sender_name AND
    t.receiver = t1_ss_address_detail.receiver_name

-- WHERE 1=1
--   AND t.<column> = '<value>'


-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_booking_vs_first_inscan_report
-- File: models/HubOps_Dashboard/t3_booking_vs_first_inscan_report.sql
-- Columns: 17 | Upstreams: 4
-- ═══════════════════════════════════════════════

SELECT
  t.date,
  t.awb_number,
  t.audit,
  t.service_type,
  t.travel_by,
  t.type,
  t.booking_cp_id,
  t.booking_cp,
  t.to_hub_id,
  t.to_hub,
  t.parent_hub_id,
  t.parent_hub_name,
  t.zone,
  t.booking_cp_pincode,  -- t2_master_hubops_bk.booking_cp_pincode
  t.to_hub_pincode,  -- t2_master_hubops_bk.to_hub_pincode
  t.distance_in_km,  -- t3_pincode_distance_matrix.distance_in_km
  t.distance_bucket  -- t3_pincode_distance_matrix.distance_in_km
FROM silver_layer.t3_booking_vs_first_inscan_report t
LEFT JOIN silver_layer.t2_master_hubops_bk t2_master_hubops_bk
  ON
    t.booking_cp_pincode = t2_master_hubops_bk.booking_cp_pincode AND
    t.to_hub_pincode = t2_master_hubops_bk.to_hub_pincode
LEFT JOIN silver_layer.t3_pincode_distance_matrix t3_pincode_distance_
  ON
    t.distance_in_km = t3_pincode_distance_.distance_in_km AND
    t.distance_bucket = t3_pincode_distance_.distance_in_km

-- WHERE 1=1
--   AND t.<column> = '<value>'


-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_incoming_shipments
-- File: models/HubOps_Dashboard/t3_incoming_shipments.sql
-- Columns: 12 | Upstreams: 3
-- ═══════════════════════════════════════════════

SELECT
  t.operation_time,
  t.awb_number,  -- t2_master_hubops.awb_number
  t.origin_hub_id,  -- t2_master_hubops_bk.origin_hub_id
  t.origin_hub_name,  -- t2_master_hubops_bk.origin_hub_name
  t.current_hub_name,  -- t2_master_hubops.premise_name
  t.destination_hub_id,  -- t2_master_hubops_bk.destination_hub_id
  t.destination_hub_name,  -- t2_master_hubops_bk.destination_hub_name
  t.status,  -- t1_ss_shipment_operation_code_master.status
  t.doc_type,  -- t2_master_hubops_bk.type
  t.mode,  -- t2_master_hubops_bk.travel_by
  t.booking_type,  -- t2_master_hubops_bk.booking_type
  t.service_type  -- t2_master_hubops_bk.service_type
FROM silver_layer.t3_incoming_shipments t
LEFT JOIN silver_layer.t2_master_hubops_bk t2_master_hubops_bk
  ON
    t.origin_hub_id = t2_master_hubops_bk.origin_hub_id AND
    t.origin_hub_name = t2_master_hubops_bk.origin_hub_name AND
    t.destination_hub_id = t2_master_hubops_bk.destination_hub_id AND
    t.destination_hub_name = t2_master_hubops_bk.destination_hub_name AND
    t.doc_type = t2_master_hubops_bk.type AND
    t.mode = t2_master_hubops_bk.travel_by AND
    t.booking_type = t2_master_hubops_bk.booking_type AND
    t.service_type = t2_master_hubops_bk.service_type
LEFT JOIN silver_layer.t2_master_hubops t2_master_hubops
  ON
    t.awb_number = t2_master_hubops.awb_number AND
    t.current_hub_name = t2_master_hubops.premise_name
LEFT JOIN silver_layer.t1_ss_shipment_operation_code_master t1_ss_shipment_opera
  ON
    t.status = t1_ss_shipment_opera.status

-- WHERE 1=1
--   AND t.<column> = '<value>'


-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_inscan_bags_report
-- File: models/HubOps_Dashboard/t3_inscan_bags_report.sql
-- Columns: 15 | Upstreams: 3
-- ═══════════════════════════════════════════════

SELECT
  t.bag_number,
  t.inscan_hub_id,  -- t2_master_hubops.premise_id
  t.inscan_hub_name,  -- t2_master_hubops.premise_name
  t.origin_hub_id,  -- t1_bgs_bag_hubops.premise_id
  t.origin_hub_name,  -- t1_prs_premise_master_hubops.premise_name
  t.destination_hub_id,
  t.destination_hub_name,  -- t1_prs_premise_master_hubops.premise_name
  t.inscan_time,
  t.user_id,  -- t2_master_hubops.user_id
  t.inscanned_by_username,
  t.bag_weight,
  t.content_type,
  t.mode,
  t.travel_by,
  t.shipment_count
FROM silver_layer.t3_inscan_bags_report t
LEFT JOIN silver_layer.t2_master_hubops t2_master_hubops
  ON
    t.inscan_hub_id = t2_master_hubops.premise_id AND
    t.inscan_hub_name = t2_master_hubops.premise_name AND
    t.user_id = t2_master_hubops.user_id
LEFT JOIN silver_layer.t1_bgs_bag_hubops t1_bgs_bag_hubops
  ON
    t.origin_hub_id = t1_bgs_bag_hubops.premise_id
LEFT JOIN silver_layer.t1_prs_premise_master_hubops t1_prs_premise_maste
  ON
    t.origin_hub_name = t1_prs_premise_maste.premise_name AND
    t.destination_hub_name = t1_prs_premise_maste.premise_name

-- WHERE 1=1
--   AND t.<column> = '<value>'


-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_inscan_shipments_report
-- File: models/HubOps_Dashboard/t3_inscan_shipments_report.sql
-- Columns: 14 | Upstreams: 2
-- ═══════════════════════════════════════════════

SELECT
  t.operation_time,  -- t2_master_hubops.operation_time
  t.premise_id,  -- t2_master_hubops.premise_id
  t.premise_name,  -- t2_master_hubops.premise_name
  t.awb_number,  -- manifest_only
  t.inscan_time,  -- manifest_only
  t.booking_cp_id,  -- manifest_only
  t.booking_cp,  -- manifest_only
  t.booking_type,  -- manifest_only
  t.service_type,  -- manifest_only
  t.travel_by,  -- manifest_only
  t.doc_type,  -- manifest_only
  t.user_email_id,  -- manifest_only
  t.outscan_time,  -- manifest_only
  t.outscan_hub  -- manifest_only
FROM silver_layer.t3_inscan_shipments_report t
LEFT JOIN silver_layer.t2_master_hubops t2_master_hubops
  ON
    t.operation_time = t2_master_hubops.operation_time AND
    t.premise_id = t2_master_hubops.premise_id AND
    t.premise_name = t2_master_hubops.premise_name

-- WHERE 1=1
--   AND t.<column> = '<value>'


-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_master_booking_hubops_delivery
-- File: models/Control_Tower_Dashboard/t3_master_booking_hubops_delivery.sql
-- Columns: 82 | Upstreams: 3
-- ═══════════════════════════════════════════════

SELECT
  t.select,
  t.booking_month,  -- t3_master_booking_hubops_delivery_pre_clean.booking_month
  t.booking_date,  -- t3_master_booking_hubops_delivery_pre_clean.booking_date
  t.booking_date_time,  -- t3_master_booking_hubops_delivery_pre_clean.booking_date_time
  t.tracking_id,  -- t3_master_booking_hubops_delivery_pre_clean.tracking_id
  t.movement_type,  -- t3_master_booking_hubops_delivery_pre_clean.movement_type
  t.status,  -- t3_master_booking_hubops_delivery_pre_clean.status
  t.customer,  -- t3_master_booking_hubops_delivery_pre_clean.customer
  t.receiver_name,  -- t3_master_booking_hubops_delivery_pre_clean.receiver_name
  t.document_type,  -- t3_master_booking_hubops_delivery_pre_clean.document_type
  t.service_type,  -- t3_master_booking_hubops_delivery_pre_clean.service_type
  t.booking_cp,  -- t3_master_booking_hubops_delivery_pre_clean.booking_cp
  t.origin_hub,  -- t3_master_booking_hubops_delivery_pre_clean.origin_hub
  t.current_location,  -- t3_shipment_current_location.premise_name
  t.next_location,  -- t3_master_booking_hubops_delivery_pre_clean.next_location
  t.destination_hub,  -- t3_master_booking_hubops_delivery_pre_clean.destination_hub
  t.latest_status_time,  -- t3_master_booking_hubops_delivery_pre_clean.latest_status_time
  t.origin_hub_inscan_at,  -- t3_master_booking_hubops_delivery_pre_clean.origin_hub_inscan_at
  t.origin_hub_outscan_at,  -- t3_master_booking_hubops_delivery_pre_clean.origin_hub_outscan_at
  t.destination_hub_inscan_at,  -- t3_master_booking_hubops_delivery_pre_clean.destination_hub_inscan_at
  t.outscan_to_destination_cp_at,  -- t3_master_booking_hubops_delivery_pre_clean.outscan_to_destination_cp_at
  t.inscan_by_destination_cp_at,  -- t3_master_booking_hubops_delivery_pre_clean.inscan_by_destination_cp_at
  t.first_attempt_time,  -- manifest_only
  t.from_pincode,  -- t3_master_booking_hubops_delivery_pre_clean.from_pincode
  t.from_city,  -- t3_master_booking_hubops_delivery_pre_clean.from_city
  t.sender_state,  -- t3_master_booking_hubops_delivery_pre_clean.sender_state
  t.from_zone,  -- t3_master_booking_hubops_delivery_pre_clean.from_zone
  t.to_pincode,  -- t3_master_booking_hubops_delivery_pre_clean.to_pincode
  t.to_city,  -- t3_master_booking_hubops_delivery_pre_clean.to_city
  t.to_state,  -- t3_master_booking_hubops_delivery_pre_clean.to_state
  t.to_zone,  -- t3_master_booking_hubops_delivery_pre_clean.to_zone
  t.delivery_attempts,  -- t3_master_booking_hubops_delivery_pre_clean.delivery_attempts
  t.shipment_value,  -- t3_master_booking_hubops_delivery_pre_clean.shipment_value
  t.booking_length,  -- t3_master_booking_hubops_delivery_pre_clean.booking_length
  t.booking_width,  -- t3_master_booking_hubops_delivery_pre_clean.booking_width
  t.booking_height,  -- t3_master_booking_hubops_delivery_pre_clean.booking_height
  t.weight_in_kg,  -- t3_master_booking_hubops_delivery_pre_clean.weight_in_kg
  t.last_undelivered_reason,  -- t3_master_booking_hubops_delivery_pre_clean.last_undelivered_reason
  t.is_closed,  -- t3_master_booking_hubops_delivery_pre_clean.is_closed
  t.Current Location (Sevasetu),  -- t3_master_booking_hubops_delivery_pre_clean.Current Location (Sevasetu)
  t.Current Status (Sevasetu),  -- t3_master_booking_hubops_delivery_pre_clean.Current Status (Sevasetu)
  t.Outscan to (Sevasetu),  -- t3_master_booking_hubops_delivery_pre_clean.Outscan to (Sevasetu)
  t.Status Time (Sevasetu),  -- t3_master_booking_hubops_delivery_pre_clean.Status Time (Sevasetu)
  t.remarks,  -- t3_master_booking_hubops_delivery_pre_clean.remarks
  t.last_drs_number,  -- t3_master_booking_hubops_delivery_pre_clean.last_drs_number
  t.last_drs_created_on,  -- t3_master_booking_hubops_delivery_pre_clean.last_drs_created_on
  t.last_terminal_status,  -- t3_master_booking_hubops_delivery_pre_clean.last_terminal_status
  t.last_terminal_status_time,  -- t3_master_booking_hubops_delivery_pre_clean.last_terminal_status_time
  t.last_terminal_status_date,  -- t3_master_booking_hubops_delivery_pre_clean.last_terminal_status_date
  t.travel_type,  -- t3_master_booking_hubops_delivery_pre_clean.travel_type
  t.is_booking_cancelled,  -- t3_master_booking_hubops_delivery_pre_clean.is_booking_cancelled
  t.last_undelivered_timestamp,  -- t3_master_booking_hubops_delivery_pre_clean.last_undelivered_timestamp
  t.origin_hub_id,  -- t3_master_booking_hubops_delivery_pre_clean.origin_hub_id
  t.destination_hub_id,  -- t3_master_booking_hubops_delivery_pre_clean.destination_hub_id
  t.is_terminal,  -- t3_master_booking_hubops_delivery_pre_clean.is_terminal
  t.current_hub_id,  -- t3_master_booking_hubops_delivery_pre_clean.current_hub_id
  t.Last DRS (Sevasetu),  -- t3_master_booking_hubops_delivery_pre_clean.Last DRS (Sevasetu)
  t.Last DRS Created On (Sevasetu),  -- t3_master_booking_hubops_delivery_pre_clean.Last DRS Created On (Sevasetu)
  t.Last Terminal Status (Sevasetu),  -- t3_master_booking_hubops_delivery_pre_clean.Last Terminal Status (Sevasetu)
  t.Last Terminal Status Time (Sevasetu),  -- t3_master_booking_hubops_delivery_pre_clean.Last Terminal Status Time (Sevasetu)
  t.latest_middle_mile_location,  -- t3_master_booking_hubops_delivery_pre_clean.latest_middle_mile_location
  t.latest_middle_mile_status,  -- t3_master_booking_hubops_delivery_pre_clean.latest_middle_mile_status
  t.latest_status_date,  -- t3_master_booking_hubops_delivery_pre_clean.latest_status_date
  t.trip_id,  -- t3_master_booking_hubops_delivery_pre_clean.trip_id
  t.stop_id,  -- t3_master_booking_hubops_delivery_pre_clean.stop_id
  t.trip_departed_at,  -- t3_master_booking_hubops_delivery_pre_clean.trip_departed_at
  t.trip_arrived_at,  -- t3_master_booking_hubops_delivery_pre_clean.trip_arrived_at
  t.vehicle_num,  -- t3_master_booking_hubops_delivery_pre_clean.vehicle_num
  t.trip_start_hub,  -- t3_master_booking_hubops_delivery_pre_clean.trip_start_hub
  t.trip_start_hub_id,  -- t3_master_booking_hubops_delivery_pre_clean.trip_start_hub_id
  t.trip_end_hub,  -- t3_master_booking_hubops_delivery_pre_clean.trip_end_hub
  t.trip_end_hub_id,  -- t3_master_booking_hubops_delivery_pre_clean.trip_end_hub_id
  t.is_middle_mile_start,  -- t3_master_booking_hubops_delivery_pre_clean.is_middle_mile_start
  t.is_last_mile_start,  -- t3_master_booking_hubops_delivery_pre_clean.is_last_mile_start
  t.anomaly_booked_after_first_scan,  -- t3_master_booking_hubops_delivery_pre_clean.anomaly_booked_after_first_scan
  t.anomaly_no_middle_mile_but_shipment_in_last_mile,  -- t3_master_booking_hubops_delivery_pre_clean.anomaly_no_middle_mile_but_shipment_in_last_mile
  t.anomaly_location_blank,  -- t3_master_booking_hubops_delivery_pre_clean.anomaly_location_blank
  t.anomaly_origin_hub_missing,  -- t3_master_booking_hubops_delivery_pre_clean.anomaly_origin_hub_missing
  t.anomaly_destination_hub_missing,  -- t3_master_booking_hubops_delivery_pre_clean.anomaly_destination_hub_missing
  t.anomaly_current_location_missing,  -- t3_master_booking_hubops_delivery_pre_clean.anomaly_current_location_missing
  t.is_anomaly,  -- manifest_only
  t.is_backfilled  -- manifest_only
FROM silver_layer.t3_master_booking_hubops_delivery t
LEFT JOIN silver_layer.t3_master_booking_hubops_delivery_pre_clean t3_master_booking_hu
  ON
    t.Current Location (Sevasetu) = t3_master_booking_hu.Current Location (Sevasetu) AND
    t.Current Status (Sevasetu) = t3_master_booking_hu.Current Status (Sevasetu) AND
    t.Last DRS (Sevasetu) = t3_master_booking_hu.Last DRS (Sevasetu) AND
    t.Last DRS Created On (Sevasetu) = t3_master_booking_hu.Last DRS Created On (Sevasetu) AND
    t.Last Terminal Status (Sevasetu) = t3_master_booking_hu.Last Terminal Status (Sevasetu) AND
    t.Last Terminal Status Time (Sevasetu) = t3_master_booking_hu.Last Terminal Status Time (Sevasetu) AND
    t.Outscan to (Sevasetu) = t3_master_booking_hu.Outscan to (Sevasetu) AND
    t.Status Time (Sevasetu) = t3_master_booking_hu.Status Time (Sevasetu) AND
    t.anomaly_booked_after_first_scan = t3_master_booking_hu.anomaly_booked_after_first_scan AND
    t.anomaly_current_location_missing = t3_master_booking_hu.anomaly_current_location_missing AND
    t.anomaly_delivered_but_ofd_time_missing_in_dispatch = t3_master_booking_hu.anomaly_delivered_but_ofd_time_missing_in_dispatch AND
    t.anomaly_delivered_but_ofd_time_missing_in_hubops = t3_master_booking_hu.anomaly_delivered_but_ofd_time_missing_in_hubops AND
    t.anomaly_destination_hub_missing = t3_master_booking_hu.anomaly_destination_hub_missing AND
    t.anomaly_location_blank = t3_master_booking_hu.anomaly_location_blank AND
    t.anomaly_no_middle_mile_but_shipment_in_last_mile = t3_master_booking_hu.anomaly_no_middle_mile_but_shipment_in_last_mile AND
    t.anomaly_origin_hub_missing = t3_master_booking_hu.anomaly_origin_hub_missing AND
    t.booking_cp = t3_master_booking_hu.booking_cp AND
    t.booking_date = t3_master_booking_hu.booking_date AND
    t.booking_date_time = t3_master_booking_hu.booking_date_time AND
    t.booking_height = t3_master_booking_hu.booking_height AND
    t.booking_length = t3_master_booking_hu.booking_length AND
    t.booking_month = t3_master_booking_hu.booking_month AND
    t.booking_type = t3_master_booking_hu.booking_type AND
    t.booking_width = t3_master_booking_hu.booking_width AND
    t.client = t3_master_booking_hu.client AND
    t.current_hub_id = t3_master_booking_hu.current_hub_id AND
    t.customer = t3_master_booking_hu.customer AND
    t.dag_type = t3_master_booking_hu.dag_type AND
    t.delivery_attempts = t3_master_booking_hu.delivery_attempts AND
    t.destination_hub = t3_master_booking_hu.destination_hub AND
    t.destination_hub_id = t3_master_booking_hu.destination_hub_id AND
    t.destination_hub_inscan_at = t3_master_booking_hu.destination_hub_inscan_at AND
    t.document_type = t3_master_booking_hu.document_type AND
    t.first_delivered_new_drs_number = t3_master_booking_hu.first_delivered_new_drs_number AND
    t.first_delivered_time = t3_master_booking_hu.first_delivered_time AND
    t.first_ofd_attempt_new_drs_number = t3_master_booking_hu.first_ofd_attempt_new_drs_number AND
    t.first_ofd_attempt_time = t3_master_booking_hu.first_ofd_attempt_time AND
    t.first_terminal_status = t3_master_booking_hu.first_terminal_status AND
    t.first_terminal_status_time = t3_master_booking_hu.first_terminal_status_time AND
    t.from_city = t3_master_booking_hu.from_city AND
    t.from_pincode = t3_master_booking_hu.from_pincode AND
    t.from_zone = t3_master_booking_hu.from_zone AND
    t.inscan_by_destination_cp_at = t3_master_booking_hu.inscan_by_destination_cp_at AND
    t.is_booking_cancelled = t3_master_booking_hu.is_booking_cancelled AND
    t.is_closed = t3_master_booking_hu.is_closed AND
    t.is_dp_client = t3_master_booking_hu.is_dp_client AND
    t.is_last_mile_start = t3_master_booking_hu.is_last_mile_start AND
    t.is_middle_mile_start = t3_master_booking_hu.is_middle_mile_start AND
    t.is_terminal = t3_master_booking_hu.is_terminal AND
    t.last_drs_created_on = t3_master_booking_hu.last_drs_created_on AND
    t.last_drs_number = t3_master_booking_hu.last_drs_number AND
    t.last_terminal_status = t3_master_booking_hu.last_terminal_status AND
    t.last_terminal_status_date = t3_master_booking_hu.last_terminal_status_date AND
    t.last_terminal_status_time = t3_master_booking_hu.last_terminal_status_time AND
    t.last_undelivered_reason = t3_master_booking_hu.last_undelivered_reason AND
    t.last_undelivered_timestamp = t3_master_booking_hu.last_undelivered_timestamp AND
    t.latest_middle_mile_location = t3_master_booking_hu.latest_middle_mile_location AND
    t.latest_middle_mile_status = t3_master_booking_hu.latest_middle_mile_status AND
    t.latest_status_date = t3_master_booking_hu.latest_status_date AND
    t.latest_status_time = t3_master_booking_hu.latest_status_time AND
    t.movement_type = t3_master_booking_hu.movement_type AND
    t.next_location = t3_master_booking_hu.next_location AND
    t.origin_hub = t3_master_booking_hu.origin_hub AND
    t.origin_hub_id = t3_master_booking_hu.origin_hub_id AND
    t.origin_hub_inscan_at = t3_master_booking_hu.origin_hub_inscan_at AND
    t.origin_hub_outscan_at = t3_master_booking_hu.origin_hub_outscan_at AND
    t.outscan_to_destination_cp_at = t3_master_booking_hu.outscan_to_destination_cp_at AND
    t.receiver_name = t3_master_booking_hu.receiver_name AND
    t.remarks = t3_master_booking_hu.remarks AND
    t.sender_state = t3_master_booking_hu.sender_state AND
    t.service_type = t3_master_booking_hu.service_type AND
    t.shipment_value = t3_master_booking_hu.shipment_value AND
    t.status = t3_master_booking_hu.status AND
    t.stop_id = t3_master_booking_hu.stop_id AND
    t.tat_in_hrs = t3_master_booking_hu.tat_in_hrs AND
    t.to_city = t3_master_booking_hu.to_city AND
    t.to_pincode = t3_master_booking_hu.to_pincode AND
    t.to_state = t3_master_booking_hu.to_state AND
    t.to_zone = t3_master_booking_hu.to_zone AND
    t.tracking_id = t3_master_booking_hu.tracking_id AND
    t.travel_type = t3_master_booking_hu.travel_type AND
    t.trip_arrived_at = t3_master_booking_hu.trip_arrived_at AND
    t.trip_departed_at = t3_master_booking_hu.trip_departed_at AND
    t.trip_end_hub = t3_master_booking_hu.trip_end_hub AND
    t.trip_end_hub_id = t3_master_booking_hu.trip_end_hub_id AND
    t.trip_id = t3_master_booking_hu.trip_id AND
    t.trip_start_hub = t3_master_booking_hu.trip_start_hub AND
    t.trip_start_hub_id = t3_master_booking_hu.trip_start_hub_id AND
    t.vehicle_num = t3_master_booking_hu.vehicle_num AND
    t.weight_in_kg = t3_master_booking_hu.weight_in_kg
LEFT JOIN silver_layer.t3_shipment_current_location t3_shipment_current_
  ON
    t.current_location = t3_shipment_current_.premise_name
LEFT JOIN silver_layer.t1_st_shipment_tat_details_hubops t1_st_shipment_tat_d
  ON
    t.planned_edd = t1_st_shipment_tat_d.planned_edd AND
    t.revised_edd = t1_st_shipment_tat_d.revised_edd

-- WHERE 1=1
--   AND t.<column> = '<value>'


-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_outscan_shipments
-- File: models/HubOps_Dashboard/t3_outscan_shipments.sql
-- Columns: 13 | Upstreams: 2
-- ═══════════════════════════════════════════════

SELECT
  t.booking_complete_time,  -- t2_master_hubops_bk.booking_complete_time
  t.operation_time,  -- t2_master_hubops.operation_time
  t.awb_number,  -- t2_master_hubops.awb_number
  t.origin_hub_id,  -- t2_master_hubops_bk.origin_hub_id
  t.origin_hub_name,  -- t2_master_hubops_bk.origin_hub_name
  t.current_hub_name,  -- t2_master_hubops.premise_name
  t.destination_hub_id,  -- t2_master_hubops_bk.destination_hub_id
  t.destination_hub_name,  -- t2_master_hubops_bk.destination_hub_name
  t.doc_type,  -- t2_master_hubops_bk.type
  t.mode,  -- t2_master_hubops_bk.travel_by
  t.booking_type,  -- t2_master_hubops_bk.booking_type
  t.service_type,  -- t2_master_hubops_bk.service_type
  t.status  -- t2_master_hubops.status
FROM silver_layer.t3_outscan_shipments t
LEFT JOIN silver_layer.t2_master_hubops t2_master_hubops
  ON
    t.operation_time = t2_master_hubops.operation_time AND
    t.awb_number = t2_master_hubops.awb_number AND
    t.current_hub_name = t2_master_hubops.premise_name AND
    t.status = t2_master_hubops.status
LEFT JOIN silver_layer.t2_master_hubops_bk t2_master_hubops_bk
  ON
    t.booking_complete_time = t2_master_hubops_bk.booking_complete_time AND
    t.origin_hub_id = t2_master_hubops_bk.origin_hub_id AND
    t.origin_hub_name = t2_master_hubops_bk.origin_hub_name AND
    t.destination_hub_id = t2_master_hubops_bk.destination_hub_id AND
    t.destination_hub_name = t2_master_hubops_bk.destination_hub_name AND
    t.doc_type = t2_master_hubops_bk.type AND
    t.mode = t2_master_hubops_bk.travel_by AND
    t.booking_type = t2_master_hubops_bk.booking_type AND
    t.service_type = t2_master_hubops_bk.service_type

-- WHERE 1=1
--   AND t.<column> = '<value>'


-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_rpt_delivery_channel_analysis
-- File: models/Dispatch_Dashboard/t3_rpt_delivery_channel_analysis.sql
-- Columns: 24 | Upstreams: 2
-- ═══════════════════════════════════════════════

SELECT
  t.oda_deliveries,
  t.business,  -- manifest_only
  t.shipment_type,  -- t1_drs_payload_final_fulfill_6M.shipmenttype
  t.awb_number,  -- t2_master_delivery_events.awb_number
  t.hub,  -- t2_master_delivery_events.hub
  t.hub_state,  -- t2_master_delivery_events.hub_state
  t.delivery_agent_channel_partner,  -- t2_master_delivery_events.delivery_agent_channel_partner
  t.cp_state,  -- t2_master_delivery_events.cp_state
  t.delivery_agent_delivery_partner,  -- t2_master_delivery_events.delivery_agent_delivery_partner
  t.dp_state,  -- t2_master_delivery_events.dp_state
  t.drs_created_at,  -- t2_master_delivery_events.drs_created_at
  t.drs_created_date,  -- t2_master_delivery_events.drs_created_at
  t.delivery_agent_id,  -- t2_master_delivery_events.delivery_agent_id
  t.delivery_agent,  -- t2_master_delivery_events.delivery_agent
  t.new_drs_number,  -- t2_master_delivery_events.new_drs_number
  t.old_drs_number,  -- t2_master_delivery_events.old_drs_number
  t.drs_creation_source,  -- t2_master_delivery_events.drs_source
  t.status_captured_at,  -- t2_master_delivery_events.status_captured_at
  t.status_capture_date,  -- t2_master_delivery_events.status_captured_at
  t.status_source,  -- t2_master_delivery_events.status_source
  t.status,  -- t2_master_delivery_events.status
  t.latitude,  -- t2_master_delivery_events.latitude
  t.longitude,  -- t2_master_delivery_events.longitude
  t.status_category  -- manifest_only
FROM silver_layer.t3_rpt_delivery_channel_analysis t
LEFT JOIN silver_layer.t2_master_delivery_events t2_master_delivery_e
  ON
    t.awb_number = t2_master_delivery_e.awb_number AND
    t.hub = t2_master_delivery_e.hub AND
    t.hub_state = t2_master_delivery_e.hub_state AND
    t.delivery_agent_channel_partner = t2_master_delivery_e.delivery_agent_channel_partner AND
    t.cp_state = t2_master_delivery_e.cp_state AND
    t.delivery_agent_delivery_partner = t2_master_delivery_e.delivery_agent_delivery_partner AND
    t.dp_state = t2_master_delivery_e.dp_state AND
    t.drs_created_at = t2_master_delivery_e.drs_created_at AND
    t.drs_created_date = t2_master_delivery_e.drs_created_at AND
    t.delivery_agent_id = t2_master_delivery_e.delivery_agent_id AND
    t.delivery_agent = t2_master_delivery_e.delivery_agent AND
    t.new_drs_number = t2_master_delivery_e.new_drs_number AND
    t.old_drs_number = t2_master_delivery_e.old_drs_number AND
    t.drs_creation_source = t2_master_delivery_e.drs_source AND
    t.status_captured_at = t2_master_delivery_e.status_captured_at AND
    t.status_capture_date = t2_master_delivery_e.status_captured_at AND
    t.status_source = t2_master_delivery_e.status_source AND
    t.status = t2_master_delivery_e.status AND
    t.latitude = t2_master_delivery_e.latitude AND
    t.longitude = t2_master_delivery_e.longitude
LEFT JOIN silver_layer.t1_drs_payload_final_fulfill_6M t1_drs_payload_final
  ON
    t.shipment_type = t1_drs_payload_final.shipmenttype

-- WHERE 1=1
--   AND t.<column> = '<value>'


-- ═══════════════════════════════════════════════
-- Model: silver_layer.t3_shipments_inscan_vs_outscan_report
-- File: models/HubOps_Dashboard/t3_shipments_inscan_vs_outscan_report.sql
-- Columns: 10 | Upstreams: 3
-- ═══════════════════════════════════════════════

SELECT
  t.date,  -- t2_master_hubops.operation_time
  t.hub_id,  -- t2_master_hubops.premise_id
  t.hub,  -- t1_prs_premise_master_hubops.premise_name
  t.zone,  -- t1_prs_premise_master_hubops.zone
  t.state,  -- t1_prs_premise_master_hubops.state
  t.total_inscan_shipments,  -- t2_master_hubops.awb_number
  t.total_inscan_shipments_weight,  -- t1_ss_shipment_dimentions_hubops_6M.weight
  t.total_outscan_shipments,  -- t2_master_hubops.awb_number
  t.total_outscan_shipments_weight,
  t.pending_shipments  -- t2_master_hubops.awb_number
FROM silver_layer.t3_shipments_inscan_vs_outscan_report t
LEFT JOIN silver_layer.t2_master_hubops t2_master_hubops
  ON
    t.date = t2_master_hubops.operation_time AND
    t.hub_id = t2_master_hubops.premise_id AND
    t.total_inscan_shipments = t2_master_hubops.awb_number AND
    t.total_outscan_shipments = t2_master_hubops.awb_number AND
    t.pending_shipments = t2_master_hubops.awb_number
LEFT JOIN silver_layer.t1_ss_shipment_dimentions_hubops_6M t1_ss_shipment_dimen
  ON
    t.total_inscan_shipments_weight = t1_ss_shipment_dimen.weight
LEFT JOIN silver_layer.t1_prs_premise_master_hubops t1_prs_premise_maste
  ON
    t.hub = t1_prs_premise_maste.premise_name AND
    t.zone = t1_prs_premise_maste.zone AND
    t.state = t1_prs_premise_maste.state

-- WHERE 1=1
--   AND t.<column> = '<value>'

