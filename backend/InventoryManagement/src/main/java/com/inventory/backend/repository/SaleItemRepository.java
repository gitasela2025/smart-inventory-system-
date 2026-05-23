package com.inventory.backend.repository;

import com.inventory.backend.model.SaleItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface SaleItemRepository extends JpaRepository<SaleItem, Integer> {

    /**
     * Find all sale items by sale ID
     * This method is automatically implemented by Spring Data JPA
     * @param saleId the sale ID to search for
     * @return List of SaleItem objects belonging to the sale
     */
    List<SaleItem> findBySaleId(Integer saleId);
}