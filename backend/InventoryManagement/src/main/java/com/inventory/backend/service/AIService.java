package com.inventory.backend.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

@Service
public class AIService {

    @Autowired
    private RestTemplate restTemplate;

    @Value("${flask.api.url:http://localhost:5000}")
    private String flaskApiUrl;

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Get restock predictions from Flask AI
     */
    public JsonNode getRestockPredictions() {
        try {
            String url = flaskApiUrl + "/api/restock-prediction";
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            return objectMapper.readTree(response.getBody());
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    /**
     * Get product movement analysis from Flask AI
     */
    public JsonNode getProductMovement() {
        try {
            String url = flaskApiUrl + "/api/product-movement";
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            return objectMapper.readTree(response.getBody());
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    /**
     * Get sales trend analysis from Flask AI
     */
    public JsonNode getSalesTrend() {
        try {
            String url = flaskApiUrl + "/api/sales-trend";
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            return objectMapper.readTree(response.getBody());
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    /**
     * Get intelligent alerts from Flask AI
     */
    public JsonNode getAlerts() {
        try {
            String url = flaskApiUrl + "/api/alerts";
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            return objectMapper.readTree(response.getBody());
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }
}