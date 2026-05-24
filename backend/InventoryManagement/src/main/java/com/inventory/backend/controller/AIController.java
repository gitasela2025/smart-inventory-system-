package com.inventory.backend.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import java.util.HashMap;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "http://localhost:3000")
public class AIController {

    @Autowired
    private RestTemplate restTemplate;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final String FLASK_URL = "http://localhost:5001/api";

    // AI Endpoints
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

    // Reports Endpoint
    @GetMapping("/reports/generate")
    public ResponseEntity<?> generateReport(@RequestParam String type, @RequestParam String range) {
        Map<String, Object> response = new HashMap<>();
        response.put("message", "Report generated successfully");
        response.put("type", type);
        response.put("range", range);
        response.put("generated_at", new java.util.Date().toString());
        response.put("data", Map.of(
                "total_sales", 1247,
                "total_revenue", 45231.50,
                "top_product", "Wireless Mouse"
        ));
        return ResponseEntity.ok(response);
    }

    // Analytics Endpoint
    @GetMapping("/analytics/summary")
    public ResponseEntity<?> getAnalytics(@RequestParam String period) {
        Map<String, Object> response = new HashMap<>();
        response.put("totalRevenue", 45231.50);
        response.put("totalSales", 1247);
        response.put("totalUnits", 4520);
        response.put("growthRate", 12.5);
        response.put("totalProducts", 54);
        response.put("lowStockItems", 8);
        response.put("avgOrderValue", 36.25);
        response.put("bestCategory", "Electronics");
        response.put("period", period);
        return ResponseEntity.ok(response);
    }
}