package com.inventory.backend.controller;

import com.inventory.backend.model.Sale;
import com.inventory.backend.model.SaleItem;
import com.inventory.backend.repository.SaleRepository;
import com.inventory.backend.repository.SaleItemRepository;
import com.inventory.backend.repository.ProductRepository;
import com.inventory.backend.repository.InventoryRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;

@RestController
@RequestMapping("/api/sales")
@CrossOrigin(origins = "http://localhost:3000")
public class SaleController {

    @Autowired
    private SaleRepository saleRepository;

    @Autowired
    private SaleItemRepository saleItemRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private InventoryRepository inventoryRepository;

    @GetMapping
    public List<Map<String, Object>> getAllSales() {
        List<Sale> sales = saleRepository.findAll();
        List<Map<String, Object>> result = new ArrayList<>();

        for (Sale sale : sales) {
            Map<String, Object> saleData = new HashMap<>();
            saleData.put("id", sale.getId());
            saleData.put("saleDate", sale.getSaleDate());
            saleData.put("totalAmount", sale.getTotalAmount());
            saleData.put("paymentMode", sale.getPaymentMode());
            result.add(saleData);
        }
        return result;
    }

    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> getSaleById(@PathVariable Integer id) {
        Optional<Sale> saleOpt = saleRepository.findById(id);

        if (!saleOpt.isPresent()) {
            return ResponseEntity.notFound().build();
        }

        Sale sale = saleOpt.get();
        Map<String, Object> result = new HashMap<>();
        result.put("id", sale.getId());
        result.put("saleDate", sale.getSaleDate());
        result.put("totalAmount", sale.getTotalAmount());
        result.put("paymentMode", sale.getPaymentMode());

        List<SaleItem> items = saleItemRepository.findBySaleId(id);
        List<Map<String, Object>> itemList = new ArrayList<>();

        for (SaleItem item : items) {
            Map<String, Object> itemData = new HashMap<>();
            var productOpt = productRepository.findById(item.getProductId());
            String productName = productOpt.isPresent() ? productOpt.get().getName() : "Unknown";

            itemData.put("productName", productName);
            itemData.put("quantity", item.getQuantity());
            itemData.put("unitPrice", item.getUnitPriceAtSale());
            itemData.put("subtotal", item.getUnitPriceAtSale().multiply(BigDecimal.valueOf(item.getQuantity())));
            itemList.add(itemData);
        }
        result.put("items", itemList);

        return ResponseEntity.ok(result);
    }

    @PostMapping
    public ResponseEntity<?> createSale(@RequestBody Map<String, Object> request) {
        try {
            System.out.println("=== CREATE SALE CALLED ===");

            @SuppressWarnings("unchecked")
            List<Map<String, Object>> items = (List<Map<String, Object>>) request.get("items");

            if (items == null || items.isEmpty()) {
                return ResponseEntity.badRequest().body(Map.of("error", "No items in sale"));
            }

            String paymentMode = (String) request.get("paymentMode");
            if (paymentMode == null) {
                paymentMode = "CASH";
            }

            System.out.println("Payment Mode: " + paymentMode);
            System.out.println("Number of items: " + items.size());

            // Calculate total from items
            BigDecimal totalAmount = BigDecimal.ZERO;

            for (Map<String, Object> item : items) {
                Integer quantity = getIntegerValue(item.get("quantity"));
                BigDecimal unitPrice = getBigDecimalValue(item.get("unitPrice"));
                totalAmount = totalAmount.add(unitPrice.multiply(BigDecimal.valueOf(quantity)));
            }

            // Create and save sale
            Sale sale = new Sale();
            sale.setSaleDate(LocalDateTime.now());
            sale.setPaymentMode(paymentMode);
            sale.setTotalAmount(totalAmount);
            Sale savedSale = saleRepository.save(sale);

            System.out.println("Sale saved with ID: " + savedSale.getId());
            System.out.println("Total Amount: " + totalAmount);

            // Process each item (DO NOT SET SUBTOTAL - MySQL generates it)
            for (Map<String, Object> item : items) {
                Integer productId = getIntegerValue(item.get("productId"));
                Integer quantity = getIntegerValue(item.get("quantity"));
                BigDecimal unitPrice = getBigDecimalValue(item.get("unitPrice"));

                System.out.println("Processing: productId=" + productId + ", qty=" + quantity + ", price=" + unitPrice);

                // Create sale item - NO SUBTOTAL SET
                SaleItem saleItem = new SaleItem();
                saleItem.setSaleId(savedSale.getId());
                saleItem.setProductId(productId);
                saleItem.setQuantity(quantity);
                saleItem.setUnitPriceAtSale(unitPrice);
                // subtotal is GENERATED by MySQL - do NOT set it!
                saleItemRepository.save(saleItem);

                // Update inventory
                var inventory = inventoryRepository.findByProductId(productId);
                if (inventory != null) {
                    int newQuantity = Math.max(inventory.getQuantity() - quantity, 0);
                    inventory.setQuantity(newQuantity);
                    inventoryRepository.save(inventory);
                    System.out.println("Inventory updated: " + newQuantity + " remaining");
                }
            }

            // Build response
            Map<String, Object> response = new HashMap<>();
            response.put("id", savedSale.getId());
            response.put("message", "Sale completed successfully");
            response.put("saleDate", savedSale.getSaleDate());
            response.put("totalAmount", savedSale.getTotalAmount());
            response.put("paymentMode", savedSale.getPaymentMode());

            return ResponseEntity.ok(response);

        } catch (Exception e) {
            System.err.println("ERROR: " + e.getMessage());
            e.printStackTrace();
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("error", e.getMessage());
            return ResponseEntity.status(500).body(errorResponse);
        }
    }

    private Integer getIntegerValue(Object value) {
        if (value == null) return 0;
        if (value instanceof Integer) return (Integer) value;
        if (value instanceof Double) return ((Double) value).intValue();
        if (value instanceof Long) return ((Long) value).intValue();
        if (value instanceof String) return Integer.parseInt((String) value);
        return 0;
    }

    private BigDecimal getBigDecimalValue(Object value) {
        if (value == null) return BigDecimal.ZERO;
        if (value instanceof BigDecimal) return (BigDecimal) value;
        if (value instanceof Integer) return BigDecimal.valueOf((Integer) value);
        if (value instanceof Double) return BigDecimal.valueOf((Double) value);
        if (value instanceof Long) return BigDecimal.valueOf((Long) value);
        if (value instanceof String) return new BigDecimal((String) value);
        return BigDecimal.ZERO;
    }
}