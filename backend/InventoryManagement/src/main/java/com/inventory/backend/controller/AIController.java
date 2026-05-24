package com.inventory.backend.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.*;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "http://localhost:3000")
public class AIController {

    @Autowired
    private RestTemplate restTemplate;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final String FLASK_URL = "http://localhost:5001/api";

    // ======================================================
    // AI ENDPOINTS - Call Flask API
    // ======================================================

    @GetMapping("/ai/restock-predictions")
    public ResponseEntity<?> getRestockPredictions() {
        try {
            String response = restTemplate.getForObject(FLASK_URL + "/restock-prediction", String.class);
            JsonNode json = objectMapper.readTree(response);
            return ResponseEntity.ok(json);
        } catch (Exception e) {
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/ai/product-movement")
    public ResponseEntity<?> getProductMovement() {
        try {
            String response = restTemplate.getForObject(FLASK_URL + "/product-movement", String.class);
            JsonNode json = objectMapper.readTree(response);
            return ResponseEntity.ok(json);
        } catch (Exception e) {
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/ai/sales-trend")
    public ResponseEntity<?> getSalesTrend() {
        try {
            String response = restTemplate.getForObject(FLASK_URL + "/sales-trend", String.class);
            JsonNode json = objectMapper.readTree(response);
            return ResponseEntity.ok(json);
        } catch (Exception e) {
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/ai/alerts")
    public ResponseEntity<?> getAlerts() {
        try {
            String response = restTemplate.getForObject(FLASK_URL + "/alerts", String.class);
            JsonNode json = objectMapper.readTree(response);
            return ResponseEntity.ok(json);
        } catch (Exception e) {
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    // ======================================================
    // REPORTS ENDPOINTS
    // ======================================================

    @GetMapping("/reports/generate")
    public ResponseEntity<?> generateReport(
            @RequestParam String type,
            @RequestParam(required = false) String range,
            @RequestParam(required = false) String startDate,
            @RequestParam(required = false) String endDate) {

        Map<String, Object> response = new HashMap<>();
        response.put("type", type);
        response.put("dateRange", range != null ? range : "custom");
        response.put("generatedAt", new Date().toString());

        // Generate report based on type
        switch (type) {
            case "daily":
                response.putAll(generateDailyReport(range));
                break;
            case "monthly":
                response.putAll(generateMonthlyReport(range));
                break;
            case "inventory":
                response.putAll(generateInventoryReport());
                break;
            case "supplier":
                response.putAll(generateSupplierReport());
                break;
            case "ai-insights":
                response.putAll(generateAIInsightsReport());
                break;
            default:
                response.putAll(generateDailyReport(range));
        }

        // Add comparative data
        response.put("comparative", getComparativeData());

        return ResponseEntity.ok(response);
    }

    @PostMapping("/reports/schedule")
    public ResponseEntity<?> scheduleReport(@RequestBody Map<String, String> request) {
        String email = request.get("email");
        String frequency = request.get("frequency");
        String reportType = request.get("reportType");

        // In production, save to database and implement email sending
        Map<String, Object> response = new HashMap<>();
        response.put("message", "Report scheduled successfully");
        response.put("email", email);
        response.put("frequency", frequency);
        response.put("reportType", reportType);
        response.put("scheduledAt", new Date().toString());

        return ResponseEntity.ok(response);
    }

    // ======================================================
    // REPORT DATA GENERATORS
    // ======================================================

    private Map<String, Object> generateDailyReport(String range) {
        Map<String, Object> result = new HashMap<>();
        List<Map<String, Object>> sales = new ArrayList<>();

        int days = 7;
        if ("30days".equals(range)) days = 30;
        if ("90days".equals(range)) days = 90;
        if ("year".equals(range)) days = 365;

        double totalRevenue = 0;
        int totalOrders = 0;
        int totalUnits = 0;

        for (int i = days; i > 0; i--) {
            double revenue = 8000 + Math.random() * 7000;
            int orders = 30 + (int)(Math.random() * 40);
            int units = 150 + (int)(Math.random() * 100);

            totalRevenue += revenue;
            totalOrders += orders;
            totalUnits += units;

            Map<String, Object> day = new HashMap<>();
            day.put("date", java.time.LocalDate.now().minusDays(i-1).toString());
            day.put("revenue", Math.round(revenue * 100.0) / 100.0);
            day.put("orders", orders);
            day.put("units", units);
            sales.add(day);
        }

        result.put("sales", sales);
        result.put("summary", Map.of(
                "totalRevenue", Math.round(totalRevenue * 100.0) / 100.0,
                "totalOrders", totalOrders,
                "totalUnits", totalUnits
        ));

        return result;
    }

    private Map<String, Object> generateMonthlyReport(String range) {
        Map<String, Object> result = new HashMap<>();
        List<Map<String, Object>> monthlyData = new ArrayList<>();

        int months = 6;
        String[] monthNames = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"};

        double totalRevenue = 0;

        for (int i = months; i > 0; i--) {
            double revenue = 30000 + Math.random() * 20000;
            totalRevenue += revenue;

            Map<String, Object> month = new HashMap<>();
            int monthIndex = java.time.LocalDate.now().minusMonths(i-1).getMonthValue() - 1;
            month.put("month", monthNames[monthIndex]);
            month.put("revenue", Math.round(revenue * 100.0) / 100.0);
            month.put("orders", 300 + (int)(Math.random() * 200));
            month.put("units", 1500 + (int)(Math.random() * 800));
            monthlyData.add(month);
        }

        result.put("monthlyData", monthlyData);
        result.put("summary", Map.of(
                "totalRevenue", Math.round(totalRevenue * 100.0) / 100.0,
                "avgMonthlyRevenue", Math.round((totalRevenue / months) * 100.0) / 100.0
        ));

        return result;
    }

    private Map<String, Object> generateInventoryReport() {
        List<Map<String, Object>> products = new ArrayList<>();

        String[][] productData = {
                {"Wireless Mouse", "45", "15", "Electronics"},
                {"USB-C Hub", "32", "15", "Electronics"},
                {"Bluetooth Earbuds", "12", "15", "Electronics"},
                {"Rice Flour", "58", "25", "Food"},
                {"Ceylon Tea", "188", "25", "Food"},
                {"A4 Paper", "134", "20", "Office"},
                {"T-Shirt", "50", "20", "Clothing"},
                {"Hammer", "146", "15", "Tools"}
        };

        int lowStockCount = 0;

        for (String[] data : productData) {
            int stock = Integer.parseInt(data[1]);
            int reorderLevel = Integer.parseInt(data[2]);
            if (stock <= reorderLevel) lowStockCount++;

            Map<String, Object> product = new HashMap<>();
            product.put("name", data[0]);
            product.put("stock", stock);
            product.put("reorderLevel", reorderLevel);
            product.put("category", data[3]);
            product.put("status", stock <= reorderLevel ? "Low Stock" : "OK");
            products.add(product);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("products", products);
        result.put("summary", Map.of(
                "totalProducts", 54,
                "lowStockItems", lowStockCount,
                "totalStockValue", 45231.50
        ));

        return result;
    }

    private Map<String, Object> generateSupplierReport() {
        List<Map<String, Object>> suppliers = new ArrayList<>();

        String[][] supplierData = {
                {"Lanka Wholesale", "45", "15", "12500", "Electronics"},
                {"CeylonTech", "32", "12", "9800", "Electronics"},
                {"Island Fresh", "58", "20", "18700", "Food"},
                {"Premier Office", "28", "10", "5600", "Office"}
        };

        for (String[] data : supplierData) {
            Map<String, Object> supplier = new HashMap<>();
            supplier.put("name", data[0]);
            supplier.put("products", Integer.parseInt(data[1]));
            supplier.put("totalOrders", Integer.parseInt(data[2]));
            supplier.put("totalValue", Double.parseDouble(data[3]));
            supplier.put("category", data[4]);
            suppliers.add(supplier);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("suppliers", suppliers);
        result.put("summary", Map.of(
                "totalSuppliers", 5,
                "totalProcurementValue", 46600.00,
                "avgLeadTime", 5
        ));

        return result;
    }

    private Map<String, Object> generateAIInsightsReport() {
        List<String> insights = Arrays.asList(
                "📈 Sales are 25% higher on weekends. Best day: Friday with 45 orders average.",
                "⚠️ CRITICAL: Wireless Mouse will run out in 3 days. Order 150 units immediately.",
                "🏆 Rice Flour is the best-selling product with 245 units sold this month.",
                "📊 ABC Analysis: 12 products (22%) generate 70% of revenue (Category A).",
                "⚡ Fast moving products: Wireless Mouse, USB Hub, Rice Flour (sell 50+ units/week).",
                "💀 Dead stock detected: 3 products with zero sales in last 90 days.",
                "🎯 AI Model Accuracy: Restock Prediction Model - 97.98% accurate.",
                "📅 Seasonality: Sales peak during weekends, lowest on Wednesdays.",
                "🏭 Top Supplier: Lanka Wholesale supplies 45% of fast-moving products.",
                "💰 Revenue is up 16.3% compared to last month. Great growth!"
        );

        Map<String, Object> result = new HashMap<>();
        result.put("insights", insights);
        result.put("summary", Map.of(
                "totalInsights", insights.size(),
                "aiModelAccuracy", "97.98%",
                "forecastPeriod", "30 days"
        ));

        return result;
    }

    private Map<String, Object> getComparativeData() {
        double currentMonth = 45231.50;
        double previousMonth = 38900.00;
        double change = ((currentMonth - previousMonth) / previousMonth) * 100;

        Map<String, Object> comparative = new HashMap<>();
        comparative.put("currentMonth", currentMonth);
        comparative.put("previousMonth", previousMonth);
        comparative.put("change", Math.round(change * 10.0) / 10.0);

        return comparative;
    }

    // ======================================================
    // ANALYTICS ENDPOINT
    // ======================================================

    @GetMapping("/analytics/summary")
    public ResponseEntity<?> getAnalytics(@RequestParam String period) {
        Map<String, Object> response = new HashMap<>();
        response.put("totalRevenue", 45231.50);
        response.put("totalSales", 1247);
        response.put("totalUnits", 4520);
        response.put("growthRate", 16.3);
        response.put("totalProducts", 54);
        response.put("lowStockItems", 8);
        response.put("avgOrderValue", 36.25);
        response.put("bestCategory", "Electronics");
        response.put("period", period);
        response.put("topProduct", "Wireless Mouse");
        response.put("topSupplier", "Lanka Wholesale Ltd");

        return ResponseEntity.ok(response);
    }
}